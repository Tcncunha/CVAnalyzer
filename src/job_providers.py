"""
Job provider base class, concrete adapters, and cascade orchestrator.

Each adapter implements search() (HTTP call → raw payload) and
normalize(payload) → list of canonical job dicts with exactly the keys:
  id, title, company, location, category, description, url, salary, created, source

The orchestrator run_cascade() iterates providers in priority order,
deduplicates by title+company+location, and stops once a target count is reached.
"""

import logging
import re
import unicodedata
from datetime import datetime, timezone

import requests
from abc import ABC, abstractmethod

log = logging.getLogger("cv-analyzer.job_providers")

TIMEOUT_SECONDS = 20

MAX_DESCRIPTION_CHARS = 320

CANONICAL_KEYS = (
    "id",
    "title",
    "company",
    "location",
    "category",
    "description",
    "url",
    "salary",
    "created",
    "source",
)


class ProviderRequestError(Exception):
    """Typed network/HTTP exception raised by providers on any request failure."""

    def __init__(self, message, *, status_code=None):
        self.status_code = status_code
        super().__init__(message)


def _collapse_whitespace(text):
    return re.sub(r"\s+", " ", text or "").strip()


def _clean_text(text):
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) > MAX_DESCRIPTION_CHARS:
        text = text[:MAX_DESCRIPTION_CHARS].rstrip() + "..."
    return text


def _format_salary_range(min_val, max_val, currency):
    if not min_val and not max_val:
        return ""
    sym = _currency_symbol(currency or "USD")
    if not min_val:
        return f"{sym} {max_val:,.0f}"
    if not max_val:
        return f"{sym} {min_val:,.0f}"
    return f"{sym} {min_val:,.0f} - {sym} {max_val:,.0f}"


_CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "BRL": "R$",
    "INR": "₹",
    "PLN": "zł",
    "CHF": "CHF",
    "CAD": "C$",
    "AUD": "A$",
    "NZD": "NZ$",
    "SGD": "S$",
    "MXN": "MX$",
    "ZAR": "R",
    "SEK": "kr",
    "NOK": "kr",
    "DKK": "kr",
    "CZK": "Kč",
    "HUF": "Ft",
    "RON": "lei",
}


def _currency_symbol(code):
    return _CURRENCY_SYMBOLS.get(code, code)


def _strip_diacritics(text):
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    return normalized.encode("ascii", "ignore").decode("ascii")


def _dedup_key(job):
    parts = " ".join(
        (
            _strip_diacritics(job.get("title", "")),
            _strip_diacritics(job.get("company", "")),
            _strip_diacritics(job.get("location", "")),
        )
    )
    return re.sub(r"\s+", " ", parts.lower().strip())


def _summarize_error(exc):
    if isinstance(exc, ProviderRequestError):
        return str(exc)
    return f"{type(exc).__name__}: {str(exc)[:120]}"


def _format_created(raw):
    if not raw:
        return ""
    text = str(raw).strip()
    if text.isdigit() and len(text) in (10, 13):
        return _epoch_to_date(text)
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group(0)
    if _is_relative_time(text):
        return text
    return text[:10]


def _epoch_to_date(text):
    try:
        seconds = int(text) if len(text) == 10 else int(text) // 1000
        return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime("%Y-%m-%d")
    except (ValueError, OverflowError, OSError):
        return text


def _is_relative_time(text):
    return bool(
        re.search(
            r"\bago\b|just now|\byesterday\b|\btoday\b",
            text,
            re.IGNORECASE,
        )
    )


# =============================================================================
# Base class
# =============================================================================


class JobProvider(ABC):
    source = ""
    timeout = TIMEOUT_SECONDS

    def __init__(self, config=None):
        self.config = config or {}

    @abstractmethod
    def search(self, limit=None):
        """Execute the HTTP call and return the raw API payload."""

    @abstractmethod
    def normalize(self, payload):
        """Return a list of canonical job dicts from the raw payload."""

    def is_configured(self):
        return True

    def _get_json(self, url, params=None, headers=None):
        try:
            resp = requests.get(
                url, params=params, headers=headers, timeout=self.timeout
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            raise ProviderRequestError("timeout") from None
        except requests.exceptions.HTTPError as exc:
            status = (
                exc.response.status_code if exc.response is not None else None
            )
            raise ProviderRequestError(
                f"http {status}" if status else "http error",
                status_code=status,
            ) from None
        except requests.exceptions.ConnectionError:
            raise ProviderRequestError("connection error") from None
        except requests.exceptions.RequestException:
            raise ProviderRequestError("request failed") from None
        except ValueError:
            raise ProviderRequestError("invalid json response") from None

    def _post_json(self, url, json_body=None, headers=None):
        try:
            resp = requests.post(
                url, json=json_body, headers=headers, timeout=self.timeout
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            raise ProviderRequestError("timeout") from None
        except requests.exceptions.HTTPError as exc:
            status = (
                exc.response.status_code if exc.response is not None else None
            )
            raise ProviderRequestError(
                f"http {status}" if status else "http error",
                status_code=status,
            ) from None
        except requests.exceptions.ConnectionError:
            raise ProviderRequestError("connection error") from None
        except requests.exceptions.RequestException:
            raise ProviderRequestError("request failed") from None
        except ValueError:
            raise ProviderRequestError("invalid json response") from None

    def _canonicalize(self, raw):
        job = {key: str(raw.get(key, "") or "") for key in CANONICAL_KEYS}
        job["description"] = _clean_text(raw.get("description", ""))
        job["source"] = self.source
        return job


# =============================================================================
# Adzuna
# =============================================================================

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"

_CURRENCY = {
    "at": "€",
    "au": "A$",
    "be": "€",
    "br": "R$",
    "ca": "C$",
    "ch": "CHF",
    "cz": "Kč",
    "de": "€",
    "dk": "kr",
    "es": "€",
    "fi": "€",
    "fr": "€",
    "gb": "£",
    "hu": "Ft",
    "ie": "€",
    "in": "₹",
    "it": "€",
    "mx": "MX$",
    "nl": "€",
    "no": "kr",
    "nz": "NZ$",
    "pl": "zł",
    "pt": "€",
    "ro": "lei",
    "se": "kr",
    "sg": "S$",
    "us": "$",
    "za": "R",
}


def _adzuna_display_name(value, key):
    if isinstance(value, dict):
        return value.get("display_name", "")
    return ""


def _adzuna_format_salary(item, country):
    symbol = _CURRENCY.get(country, "$")
    salary_min = item.get("salary_min") or -1
    salary_max = item.get("salary_max") or -1
    if salary_min < 0 and salary_max < 0:
        return ""
    if salary_min < 0:
        return f"{symbol} {salary_max:,.0f}"
    if salary_max < 0:
        return f"{symbol} {salary_min:,.0f}"
    return f"{symbol} {salary_min:,.0f} - {symbol} {salary_max:,.0f}"


class AdzunaProvider(JobProvider):
    source = "adzuna"

    def is_configured(self):
        return bool(
            str(self.config.get("adzuna_app_id", "") or "").strip()
            and str(self.config.get("adzuna_app_key", "") or "").strip()
        )

    def search(self, limit=None):
        params = {
            "app_id": self.config["adzuna_app_id"].strip(),
            "app_key": self.config["adzuna_app_key"].strip(),
            "results_per_page": self.config.get("results_per_page", 20),
            "what": self.config.get("query", ""),
            "content-type": "application/json",
        }
        if limit is not None:
            params["results_per_page"] = min(
                params["results_per_page"], max(1, int(limit))
            )
        location = self.config.get("location", "").strip()
        if location:
            params["where"] = location
        country = self.config.get("country", "br")
        return self._get_json(
            f"{ADZUNA_BASE_URL}/{country}/search/1", params=params
        )

    def normalize(self, payload):
        if not isinstance(payload, dict):
            return []
        country = self.config.get("country", "br")
        jobs = []
        for idx, item in enumerate(payload.get("results", [])):
            raw = {
                "id": item.get("id", idx),
                "title": item.get("title", ""),
                "company": _adzuna_display_name(item.get("company"), "company"),
                "location": _adzuna_display_name(item.get("location"), "location"),
                "category": _adzuna_display_name(item.get("category"), "category"),
                "description": item.get("description", ""),
                "url": item.get("redirect_url", ""),
                "salary": _adzuna_format_salary(item, country),
                "created": _format_created(item.get("created", "")),
            }
            jobs.append(self._canonicalize(raw))
        return jobs


# =============================================================================
# Himalayas
# =============================================================================

HIMALAYAS_BASE_URL = "https://himalayas.app/jobs/api/search"

_SALARY_PERIOD_SUFFIX = {
    "hourly": "/hr",
    "weekly": "/wk",
    "fortnightly": "/2wk",
    "monthly": "/mo",
    "annual": "/yr",
}


class HimalayasProvider(JobProvider):
    source = "himalayas"

    def search(self, limit=None):
        params = {"page": "1"}
        query = self.config.get("query", "")
        if query:
            params["q"] = query
        country = self.config.get("country", "")
        if country:
            params["country"] = country
        params["sort"] = "relevant"
        return self._get_json(HIMALAYAS_BASE_URL, params=params)

    def normalize(self, payload):
        if not isinstance(payload, dict):
            return []
        jobs = []
        for item in payload.get("jobs", []):
            currency = item.get("currency") or ""
            min_sal = item.get("minSalary")
            max_sal = item.get("maxSalary")
            period = item.get("salaryPeriod", "annual")
            suffix = _SALARY_PERIOD_SUFFIX.get(period, "/yr")
            salary_str = ""
            if (min_sal or max_sal) and currency:
                salary_str = _format_salary_range(min_sal, max_sal, currency)
                if salary_str and suffix != "/yr":
                    salary_str += suffix
            locations = item.get("locationRestrictions") or []
            location_str = ", ".join(locations) if locations else "Remote"
            categories = item.get("categories") or []
            category_str = ", ".join(categories)
            seniority = item.get("seniority") or ""
            if isinstance(seniority, list):
                seniority = ", ".join(str(level) for level in seniority)
            title = item.get("title", "")
            if seniority:
                title = f"{title} ({seniority})"
            raw = {
                "id": item.get("guid", ""),
                "title": title,
                "company": item.get("companyName", ""),
                "location": location_str,
                "category": category_str,
                "description": item.get("description", ""),
                "url": item.get("applicationLink", ""),
                "salary": salary_str,
                "created": _format_created(item.get("pubDate", "")),
            }
            jobs.append(self._canonicalize(raw))
        return jobs


# =============================================================================
# Arbeitnow
# =============================================================================

ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"
ARBEITNOW_URL_UK = "https://www.arbeitnow.co.uk/api/job-board-api"


class ArbeitnowProvider(JobProvider):
    source = "arbeitnow"

    def search(self, limit=None):
        country = self.config.get("country", "")
        url = ARBEITNOW_URL_UK if country in ("gb", "uk") else ARBEITNOW_URL
        payload = self._get_json(url)
        query = self.config.get("query", "").strip().lower()
        if query and isinstance(payload, dict):
            keywords = [k.strip() for k in re.split(r"\s+", query) if k.strip()]
            if keywords:
                filtered = []
                for item in payload.get("data", []):
                    text = (
                        str(item.get("title", ""))
                        + " "
                        + str(item.get("description", ""))
                    ).lower()
                    if all(kw in text for kw in keywords):
                        filtered.append(item)
                payload["data"] = filtered
        return payload

    def normalize(self, payload):
        if not isinstance(payload, dict):
            return []
        jobs = []
        for item in payload.get("data", []):
            raw = {
                "id": item.get("slug", ""),
                "title": item.get("title", ""),
                "company": item.get("company_name", ""),
                "location": item.get("location", ""),
                "category": ", ".join(item.get("tags") or []),
                "description": item.get("description", ""),
                "url": item.get("url", ""),
                "salary": str(item.get("salary", "")),
                "created": _format_created(item.get("created_at", "")),
            }
            jobs.append(self._canonicalize(raw))
        return jobs


# =============================================================================
# SerpApi (optional, P1)
# =============================================================================

SERPAPI_URL = "https://serpapi.com/search.json"


class SerpApiProvider(JobProvider):
    source = "serpapi"

    def is_configured(self):
        return bool(str(self.config.get("serpapi_api_key", "") or "").strip())

    def search(self, limit=None):
        params = {
            "engine": "google_jobs",
            "q": self.config.get("query", ""),
            "api_key": self.config["serpapi_api_key"].strip(),
        }
        location = self.config.get("location", "").strip()
        if location:
            params["location"] = location
        return self._get_json(SERPAPI_URL, params=params)

    def normalize(self, payload):
        if not isinstance(payload, dict):
            return []
        jobs = []
        for item in payload.get("jobs_results", []):
            extensions = item.get("detected_extensions") or {}
            salary = extensions.get("salary") or ""
            posted = extensions.get("posted_at") or ""
            raw = {
                "id": item.get("job_id", ""),
                "title": item.get("title", ""),
                "company": item.get("company_name", ""),
                "location": item.get("location", ""),
                "category": "",
                "description": item.get("description", ""),
                "url": item.get("share_link") or item.get("apply_link") or "",
                "salary": salary,
                "created": _format_created(posted),
            }
            jobs.append(self._canonicalize(raw))
        return jobs


# =============================================================================
# Jooble (optional, P1)
# =============================================================================


def _jooble_domain(country):
    mapping = {
        "us": "us",
        "gb": "uk",
        "uk": "uk",
        "de": "de",
        "br": "br",
        "au": "au",
    }
    return mapping.get(country, "us")


class JoobleProvider(JobProvider):
    source = "jooble"

    def is_configured(self):
        return bool(str(self.config.get("jooble_api_key", "") or "").strip())

    def search(self, limit=None):
        country = self.config.get("country", "us")
        domain = _jooble_domain(country)
        url = f"https://{domain}.jooble.org/api/{self.config['jooble_api_key'].strip()}"
        body = {
            "keywords": self.config.get("query", ""),
            "location": self.config.get("location", ""),
            "page": 1,
        }
        return self._post_json(url, json_body=body)

    def normalize(self, payload):
        if not isinstance(payload, dict):
            return []
        jobs = []
        for item in payload.get("jobs", []):
            raw = {
                "id": item.get("id", ""),
                "title": item.get("title", ""),
                "company": item.get("company", ""),
                "location": item.get("location", ""),
                "category": item.get("source", ""),
                "description": item.get("snippet", ""),
                "url": item.get("link", ""),
                "salary": "",
                "created": _format_created(item.get("date", "")),
            }
            jobs.append(self._canonicalize(raw))
        return jobs


# =============================================================================
# USAJobs (optional, P1) — country=us only
# =============================================================================

USAJOBS_URL = "https://data.usajobs.gov/api/search"
USAJOBS_USER_AGENT = "cv-analyzer-job-search"


class USAJobsProvider(JobProvider):
    source = "usajobs"

    def is_configured(self):
        country = str(self.config.get("country", "") or "")
        return bool(
            country == "us"
            and str(self.config.get("usajobs_api_key", "") or "").strip()
        )

    def search(self, limit=None):
        headers = {
            "User-Agent": USAJOBS_USER_AGENT,
            "Authorization": f"Bearer {self.config['usajobs_api_key'].strip()}",
        }
        params = {"Keyword": self.config.get("query", "")}
        location = self.config.get("location", "").strip()
        if location:
            params["LocationName"] = location
        if limit is not None:
            params["ResultsPerPage"] = max(1, min(50, int(limit)))
        return self._get_json(USAJOBS_URL, params=params, headers=headers)

    def normalize(self, payload):
        if not isinstance(payload, dict):
            return []
        search_result = payload.get("SearchResult", {})
        items = search_result.get("SearchResultItems", [])
        jobs = []
        for item in items:
            desc = item.get("MatchedObjectDescriptor", {})
            salary_min = desc.get("PositionRemuneration", [{}])
            salary_str = ""
            if salary_min and isinstance(salary_min, list):
                rem = salary_min[0]
                low = rem.get("MinimumRange", "")
                high = rem.get("MaximumRange", "")
                unit = rem.get("RateIntervalCode", "")
                if low or high:
                    salary_str = f"{low}-{high} {unit}".strip()
            raw = {
                "id": desc.get("PositionID", ""),
                "title": desc.get("PositionTitle", ""),
                "company": desc.get("OrganizationName", ""),
                "location": desc.get("PositionLocationDisplay", ""),
                "category": "",
                "description": desc.get("QualificationSummary", ""),
                "url": desc.get("PositionURI", ""),
                "salary": salary_str,
                "created": _format_created(
                    desc.get("PublicationStartDate", "")
                ),
            }
            jobs.append(self._canonicalize(raw))
        return jobs


# =============================================================================
# Cascade orchestration
# =============================================================================

CASCADE_ORDER = [
    AdzunaProvider,
    HimalayasProvider,
    SerpApiProvider,
    JoobleProvider,
    ArbeitnowProvider,
    USAJobsProvider,
]


def run_cascade(config, target):
    jobs = []
    seen = set()
    coverage = {}
    calls = {}
    errors = {}
    reached_target = False

    for provider_cls in CASCADE_ORDER:
        if len(jobs) >= target:
            reached_target = True
            break

        provider = provider_cls(config)
        source = provider.source
        try:
            if not provider.is_configured():
                continue
            remaining = target - len(jobs)
            calls[source] = calls.get(source, 0) + 1
            payload = provider.search(limit=remaining)
            items = provider.normalize(payload)
        except Exception as exc:
            errors[source] = _summarize_error(exc)
            log.warning("Provider %s failed: %s", source, exc)
            continue

        for item in items:
            if len(jobs) >= target:
                reached_target = True
                break
            key = _dedup_key(item)
            if key in seen:
                continue
            seen.add(key)
            jobs.append(item)
            coverage[source] = coverage.get(source, 0) + 1

    if len(jobs) >= target:
        reached_target = True

    return {
        "jobs": jobs,
        "coverage": coverage,
        "calls": calls,
        "errors": errors,
        "reached_target": reached_target,
    }
