"""Tests for job_providers (cascade orchestrator, adapters, dedup, metadata)."""

import pytest
import requests

from job_providers import (
    AdzunaProvider,
    ArbeitnowProvider,
    HimalayasProvider,
    JoobleProvider,
    JobProvider,
    ProviderRequestError,
    SerpApiProvider,
    USAJobsProvider,
    _dedup_key,
    _format_salary_range,
    _summarize_error,
    _collapse_whitespace,
    _format_created,
    _clean_text,
    run_cascade,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _adzuna_config(**overrides):
    cfg = {
        "query": "python",
        "location": "Sao Paulo",
        "country": "br",
        "results_per_page": 10,
        "adzuna_app_id": "app-id",
        "adzuna_app_key": "app-key",
    }
    cfg.update(overrides)
    return cfg


def _adzuna_payload(n=3):
    results = []
    for i in range(n):
        results.append({
            "id": f"job-{i}",
            "title": f"Python Dev {i}",
            "company": {"display_name": f"Company {i}"},
            "location": {"display_name": f"Location {i}"},
            "category": {"display_name": "IT"},
            "description": f"Description for job {i}",
            "redirect_url": f"https://example.com/{i}",
            "salary_min": 5000,
            "salary_max": 10000,
            "created": "2026-09-01T12:00:00Z",
        })
    return {"results": results, "count": len(results)}


def _himalayas_payload(n=3):
    jobs = []
    for i in range(n):
        jobs.append({
            "title": f"React Engineer {i}",
            "companyName": f"TechCo {i}",
            "minSalary": 80000,
            "maxSalary": 120000,
            "salaryPeriod": "annual",
            "currency": "USD",
            "seniority": "Senior",
            "categories": ["Engineering"],
            "locationRestrictions": ["US", "UK"],
            "description": f"<p>Job description {i}</p>",
            "pubDate": 1725000000000,
            "applicationLink": f"https://himalayas.app/jobs/{i}",
            "guid": f"himalayas-{i}",
        })
    return {"totalCount": len(jobs), "jobs": jobs}


def _arbeitnow_payload(n=3):
    data = []
    for i in range(n):
        data.append({
            "slug": f"job-slug-{i}",
            "title": f"Backend Dev {i}",
            "company_name": f"Startup {i}",
            "description": f"Looking for backend engineer {i}",
            "url": f"https://www.arbeitnow.com/jobs/{i}",
            "tags": ["Python", "Django"],
            "job_types": ["Full Time"],
            "salary": "60000 EUR",
            "created_at": 1725000000,
            "location": "Berlin, Germany",
        })
    return {"data": data, "meta": {"count": len(data)}}


def _serpapi_payload(n=3):
    results = []
    for i in range(n):
        results.append({
            "job_id": f"serp-{i}",
            "title": f"ML Engineer {i}",
            "company_name": f"AI Corp {i}",
            "location": "New York, NY",
            "description": f"Machine learning role {i}",
            "share_link": f"https://serpapi.com/jobs/{i}",
            "apply_link": f"https://apply.com/{i}",
            "detected_extensions": {
                "salary": "$150,000 - $200,000",
                "posted_at": "2 days ago",
            },
        })
    return {"jobs_results": results}


def _jooble_payload(n=3):
    jobs = []
    for i in range(n):
        jobs.append({
            "id": f"jooble-{i}",
            "title": f"Data Analyst {i}",
            "company": f"DataCo {i}",
            "location": "Remote",
            "source": "linkedin.com",
            "snippet": f"Analyze data for project {i}",
            "link": f"https://jooble.org/job/{i}",
            "date": "2026-09-01",
        })
    return {"totalCount": len(jobs), "jobs": jobs}


def _usajobs_payload(n=3):
    items = []
    for i in range(n):
        items.append({
            "MatchedObjectDescriptor": {
                "PositionID": f"USA-{i}",
                "PositionTitle": f"IT Specialist {i}",
                "OrganizationName": "Department of Defense",
                "PositionLocationDisplay": "Washington, DC",
                "QualificationSummary": f"IT role {i}",
                "PositionURI": f"https://usajobs.gov/job/{i}",
                "PublicationStartDate": "2026-09-01T00:00:00",
                "PositionRemuneration": [{
                    "MinimumRange": "70000",
                    "MaximumRange": "100000",
                    "RateIntervalCode": "Per Year",
                }],
            }
        })
    return {
        "SearchResult": {
            "SearchResultItems": items,
            "SearchResultCount": str(n),
        }
    }


# ---------------------------------------------------------------------------
# Text normalization helpers
# ---------------------------------------------------------------------------

class TestCollapseWhitespace:
    def test_normalizes_spaces(self):
        assert _collapse_whitespace("  hello   world  ") == "hello world"

    def test_newlines_and_tabs(self):
        assert _collapse_whitespace("line1\nline2\tline3") == "line1 line2 line3"

    def test_empty_string(self):
        assert _collapse_whitespace("") == ""

    def test_none(self):
        assert _collapse_whitespace(None) == ""


class TestTruncateDescription:
    def test_short_text_unchanged(self):
        assert _clean_text("short") == "short"

    def test_long_text_truncated(self):
        text = "a" * 400
        result = _clean_text(text)
        assert len(result) <= 324
        assert result.endswith("...")

    def test_collapses_whitespace(self):
        assert _clean_text("  a  b  ") == "a b"


class TestCleanTextSingleSource:
    def test_job_search_reexports_same_object(self):
        import job_search

        assert job_search._clean_text is _clean_text

    def test_job_search_max_chars_constant(self):
        import job_search

        assert job_search.MAX_DESCRIPTION_CHARS == 320

    def test_job_search_behavior_unchanged(self):
        import job_search

        assert job_search._clean_text("  a  b  ") == "a b"
        result = job_search._clean_text("x" * 400)
        assert len(result) <= 324
        assert result.endswith("...")

    def test_boundary_320_not_truncated(self):
        assert len(_clean_text("y" * 320)) == 320
        result = _clean_text("y" * 321)
        assert len(result) <= 324
        assert result.endswith("...")


class TestFormatSalaryRange:
    def test_both_values(self):
        assert _format_salary_range(50000, 80000, "$") == "$ 50,000 - $ 80,000"

    def test_only_min(self):
        assert _format_salary_range(50000, None, "€") == "€ 50,000"

    def test_only_max(self):
        assert _format_salary_range(None, 80000, "£") == "£ 80,000"

    def test_neither(self):
        assert _format_salary_range(None, None, "$") == ""


class TestFormatCreated:
    def test_iso_date(self):
        assert _format_created("2026-09-01T12:00:00Z") == "2026-09-01"

    def test_plain_date(self):
        assert _format_created("2026-09-01") == "2026-09-01"

    def test_empty(self):
        assert _format_created("") == ""

    def test_epoch_seconds(self):
        assert _format_created("1725000000") == "2024-08-30"

    def test_epoch_milliseconds(self):
        assert _format_created("1725000000000") == "2024-08-30"

    def test_epoch_numeric_int_input(self):
        assert _format_created(1725000000) == "2024-08-30"

    def test_relative_string_not_truncated(self):
        assert _format_created("2 days ago") == "2 days ago"
        assert _format_created("3 hours ago") == "3 hours ago"

    def test_none(self):
        assert _format_created(None) == ""


class TestDedupKey:
    def test_basic(self):
        job = {"title": "Python Dev", "company": "Acme Corp", "location": "Berlin"}
        assert _dedup_key(job) == "python dev acme corp berlin"

    def test_case_insensitive(self):
        j1 = {"title": "Engineer", "company": "Google", "location": "NYC"}
        j2 = {"title": "engineer", "company": "google", "location": "nyc"}
        assert _dedup_key(j1) == _dedup_key(j2)

    def test_whitespace_collapsed(self):
        j1 = {"title": "  Python   Dev  ", "company": "Acme", "location": "Remote"}
        j2 = {"title": "Python Dev", "company": "Acme", "location": "Remote"}
        assert _dedup_key(j1) == _dedup_key(j2)

    def test_different_items_different_keys(self):
        j1 = {"title": "Python Dev", "company": "Acme", "location": "Berlin"}
        j2 = {"title": "Java Dev", "company": "Acme", "location": "Berlin"}
        assert _dedup_key(j1) != _dedup_key(j2)

    def test_accents_normalized(self):
        with_accents = {
            "title": "Engenheiro de Software",
            "company": "Ação Empresa",
            "location": "São Paulo",
        }
        without_accents = {
            "title": "Engenheiro de Software",
            "company": "Acao Empresa",
            "location": "Sao Paulo",
        }
        assert _dedup_key(with_accents) == _dedup_key(without_accents)

    def test_diacritics_stripped_from_key(self):
        job = {"title": "Café", "company": "München GmbH", "location": "Żory"}
        key = _dedup_key(job)
        assert "é" not in key and "ü" not in key and "ż" not in key


class TestSummarizeError:
    def test_provider_request_error(self):
        exc = ProviderRequestError("timeout")
        assert _summarize_error(exc) == "timeout"

    def test_provider_request_error_with_status(self):
        exc = ProviderRequestError("http 429", status_code=429)
        assert _summarize_error(exc) == "http 429"

    def test_generic_exception(self):
        exc = RuntimeError("some internal error")
        result = _summarize_error(exc)
        assert "RuntimeError" in result
        assert "some internal error" in result

    def test_no_key_leak(self):
        exc = ProviderRequestError("request failed")
        summary = _summarize_error(exc)
        assert "app-id" not in summary
        assert "app-key" not in summary
        assert "api_key" not in summary


# ---------------------------------------------------------------------------
# ProviderRequestError
# ---------------------------------------------------------------------------

class TestProviderRequestError:
    def test_message(self):
        exc = ProviderRequestError("timeout")
        assert str(exc) == "timeout"

    def test_status_code_none(self):
        exc = ProviderRequestError("connection error")
        assert exc.status_code is None

    def test_status_code_set(self):
        exc = ProviderRequestError("rate limited", status_code=429)
        assert exc.status_code == 429


# ---------------------------------------------------------------------------
# JobProvider base class
# ---------------------------------------------------------------------------

class TestJobProviderBase:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            JobProvider({})

    def test_requires_search_and_normalize(self):
        class PartialProvider(JobProvider):
            source = "partial"

            def search(self, limit=None):
                return {}

        with pytest.raises(TypeError):
            PartialProvider({})

    def test_timeout_default(self):
        assert JobProvider.timeout == 20

    def test_canonicalize_fills_missing_fields(self):
        class DummyProvider(JobProvider):
            source = "dummy"

            def search(self, limit=None):
                return {}

            def normalize(self, payload):
                return [self._canonicalize({"id": "123", "title": "Dev"})]

        provider = DummyProvider({})
        jobs = provider.normalize({})
        assert jobs[0]["id"] == "123"
        assert jobs[0]["title"] == "Dev"
        assert jobs[0]["company"] == ""
        assert jobs[0]["location"] == ""
        assert jobs[0]["category"] == ""
        assert jobs[0]["description"] == ""
        assert jobs[0]["url"] == ""
        assert jobs[0]["salary"] == ""
        assert jobs[0]["created"] == ""
        assert jobs[0]["source"] == "dummy"

    def test_canonicalize_truncates_description(self):
        class DummyProvider(JobProvider):
            source = "dummy"

            def search(self, limit=None):
                return {}

            def normalize(self, payload):
                return [self._canonicalize({"title": "t", "description": "x" * 500})]

        provider = DummyProvider({})
        job = provider.normalize({})[0]
        assert job["description"].endswith("...")
        assert len(job["description"]) <= 324

    def test_canonicalize_collapses_whitespace(self):
        class DummyProvider(JobProvider):
            source = "dummy"

            def search(self, limit=None):
                return {}

            def normalize(self, payload):
                return [self._canonicalize({"title": "t", "description": "  line1\n  line2  "})]

        provider = DummyProvider({})
        job = provider.normalize({})[0]
        assert job["description"] == "line1 line2"


# ---------------------------------------------------------------------------
# AdzunaProvider
# ---------------------------------------------------------------------------

class TestAdzunaProvider:
    def test_is_configured_with_keys(self):
        provider = AdzunaProvider(_adzuna_config())
        assert provider.is_configured()

    def test_not_configured_without_keys(self):
        provider = AdzunaProvider({"adzuna_app_id": "", "adzuna_app_key": ""})
        assert not provider.is_configured()

    def test_not_configured_missing_keys(self):
        provider = AdzunaProvider({})
        assert not provider.is_configured()

    def test_not_configured_with_none_keys(self):
        provider = AdzunaProvider({"adzuna_app_id": None, "adzuna_app_key": None})
        assert not provider.is_configured()

    def test_normalize_returns_canonical_keys(self):
        provider = AdzunaProvider(_adzuna_config())
        payload = _adzuna_payload(1)
        jobs = provider.normalize(payload)
        assert len(jobs) == 1
        assert set(jobs[0].keys()) == {
            "id", "title", "company", "location", "category",
            "description", "url", "salary", "created", "source",
        }

    def test_source_is_adzuna(self):
        provider = AdzunaProvider(_adzuna_config())
        jobs = provider.normalize(_adzuna_payload(1))
        assert jobs[0]["source"] == "adzuna"

    def test_normalize_company_from_nested(self):
        provider = AdzunaProvider(_adzuna_config())
        jobs = provider.normalize(_adzuna_payload(1))
        assert jobs[0]["company"] == "Company 0"

    def test_normalize_invalid_payload(self):
        provider = AdzunaProvider(_adzuna_config())
        assert provider.normalize(None) == []
        assert provider.normalize("invalid") == []
        assert provider.normalize({}) == []

    def test_normalize_empty_results(self):
        provider = AdzunaProvider(_adzuna_config())
        assert provider.normalize({"results": [], "count": 0}) == []

    def test_search_raises_on_network_error(self, monkeypatch):
        def boom(*a, **k):
            raise requests.ConnectionError("network down")
        monkeypatch.setattr(requests, "get", boom)
        provider = AdzunaProvider(_adzuna_config())
        with pytest.raises(ProviderRequestError):
            provider.search()

    def test_search_raises_timeout(self, monkeypatch):
        def boom(*a, **k):
            raise requests.Timeout("timed out")
        monkeypatch.setattr(requests, "get", boom)
        provider = AdzunaProvider(_adzuna_config())
        with pytest.raises(ProviderRequestError, match="timeout"):
            provider.search()

    def test_search_raises_http_error(self, monkeypatch):
        response = requests.Response()
        response.status_code = 429
        response._content = b"rate limited"

        def boom(*a, **k):
            exc = requests.HTTPError(response=response)
            raise exc
        monkeypatch.setattr(requests, "get", boom)
        provider = AdzunaProvider(_adzuna_config())
        with pytest.raises(ProviderRequestError) as exc_info:
            provider.search()
        assert exc_info.value.status_code == 429

    def test_country_default_is_br(self):
        provider = AdzunaProvider({"adzuna_app_id": "i", "adzuna_app_key": "k"})
        assert provider.config.get("country", "br") == "br"

    def test_limit_clamps_results_per_page(self, monkeypatch):
        captured = {}

        def mock_get(url, params=None, **k):
            captured["params"] = params
            resp = requests.Response()
            resp.status_code = 200
            resp._content = __import__("json").dumps(_adzuna_payload(2)).encode()
            resp.encoding = "utf-8"
            return resp

        monkeypatch.setattr(requests, "get", mock_get)
        config = _adzuna_config(results_per_page=50)
        provider = AdzunaProvider(config)
        provider.search(limit=3)
        assert captured["params"]["results_per_page"] == 3


# ---------------------------------------------------------------------------
# HimalayasProvider
# ---------------------------------------------------------------------------

class TestHimalayasProvider:
    def test_is_configured_always(self):
        provider = HimalayasProvider({})
        assert provider.is_configured()

    def test_normalize_canonical_keys(self):
        provider = HimalayasProvider({"query": "python"})
        jobs = provider.normalize(_himalayas_payload(1))
        assert len(jobs) == 1
        assert set(jobs[0].keys()) == {
            "id", "title", "company", "location", "category",
            "description", "url", "salary", "created", "source",
        }

    def test_source_is_himalayas(self):
        provider = HimalayasProvider({})
        jobs = provider.normalize(_himalayas_payload(1))
        assert jobs[0]["source"] == "himalayas"

    def test_salary_includes_seniority(self):
        provider = HimalayasProvider({})
        jobs = provider.normalize(_himalayas_payload(1))
        assert "Senior" in jobs[0]["title"]

    def test_seniority_list_joined(self):
        payload = {
            "jobs": [{
                "title": "React Engineer",
                "companyName": "TechCo",
                "minSalary": 80000,
                "maxSalary": 120000,
                "salaryPeriod": "annual",
                "currency": "USD",
                "seniority": ["Senior", "Lead"],
                "categories": ["Engineering"],
                "locationRestrictions": ["US"],
                "description": "desc",
                "pubDate": 1725000000000,
                "applicationLink": "https://himalayas.app/jobs/x",
                "guid": "g1",
            }]
        }
        provider = HimalayasProvider({})
        jobs = provider.normalize(payload)
        assert jobs[0]["title"] == "React Engineer (Senior, Lead)"

    def test_seniority_empty_list(self):
        payload = {
            "jobs": [{
                "title": "React Engineer",
                "companyName": "TechCo",
                "seniority": [],
                "categories": [],
                "locationRestrictions": [],
                "description": "desc",
                "applicationLink": "https://himalayas.app/jobs/x",
                "guid": "g2",
            }]
        }
        provider = HimalayasProvider({})
        jobs = provider.normalize(payload)
        assert jobs[0]["title"] == "React Engineer"

    def test_salary_formatted(self):
        provider = HimalayasProvider({})
        jobs = provider.normalize(_himalayas_payload(1))
        assert "$" in jobs[0]["salary"]
        assert "80,000" in jobs[0]["salary"]

    def test_location_from_restrictions(self):
        provider = HimalayasProvider({})
        jobs = provider.normalize(_himalayas_payload(1))
        assert "US" in jobs[0]["location"]
        assert "UK" in jobs[0]["location"]

    def test_url_is_application_link(self):
        provider = HimalayasProvider({})
        jobs = provider.normalize(_himalayas_payload(1))
        assert "himalayas.app/jobs/0" in jobs[0]["url"]

    def test_normalize_invalid_payload(self):
        provider = HimalayasProvider({})
        assert provider.normalize(None) == []
        assert provider.normalize("bad") == []

    def test_normalize_empty_jobs(self):
        provider = HimalayasProvider({})
        assert provider.normalize({"jobs": []}) == []

    def test_search_raises_on_network_error(self, monkeypatch):
        def boom(*a, **k):
            raise requests.ConnectionError("down")
        monkeypatch.setattr(requests, "get", boom)
        provider = HimalayasProvider({"query": "python"})
        with pytest.raises(ProviderRequestError):
            provider.search()

    def test_category_from_categories_list(self):
        provider = HimalayasProvider({})
        jobs = provider.normalize(_himalayas_payload(1))
        assert jobs[0]["category"] == "Engineering"


# ---------------------------------------------------------------------------
# ArbeitnowProvider
# ---------------------------------------------------------------------------

class TestArbeitnowProvider:
    def test_is_configured_always(self):
        provider = ArbeitnowProvider({})
        assert provider.is_configured()

    def test_normalize_canonical_keys(self):
        provider = ArbeitnowProvider({"query": "python"})
        jobs = provider.normalize(_arbeitnow_payload(1))
        assert len(jobs) == 1
        assert set(jobs[0].keys()) == {
            "id", "title", "company", "location", "category",
            "description", "url", "salary", "created", "source",
        }

    def test_source_is_arbeitnow(self):
        provider = ArbeitnowProvider({})
        jobs = provider.normalize(_arbeitnow_payload(1))
        assert jobs[0]["source"] == "arbeitnow"

    def test_url_preserved(self):
        provider = ArbeitnowProvider({})
        jobs = provider.normalize(_arbeitnow_payload(1))
        assert "arbeitnow.com" in jobs[0]["url"]

    def test_salary_raw_string(self):
        provider = ArbeitnowProvider({})
        jobs = provider.normalize(_arbeitnow_payload(1))
        assert jobs[0]["salary"] == "60000 EUR"

    def test_category_from_tags(self):
        provider = ArbeitnowProvider({})
        jobs = provider.normalize(_arbeitnow_payload(1))
        assert "Python" in jobs[0]["category"]

    def test_search_filters_by_keyword(self, monkeypatch):
        all_data = [
            {"slug": "1", "title": "Python Dev", "company_name": "A",
             "description": "python backend", "url": "https://example.com/1",
             "tags": [], "job_types": [], "created_at": 123, "location": "Berlin"},
            {"slug": "2", "title": "Java Dev", "company_name": "B",
             "description": "java spring", "url": "https://example.com/2",
             "tags": [], "job_types": [], "created_at": 123, "location": "Munich"},
        ]

        def mock_get(url, **k):
            resp = requests.Response()
            resp.status_code = 200
            resp._content = __import__("json").dumps({"data": all_data}).encode()
            resp.encoding = "utf-8"
            return resp

        monkeypatch.setattr(requests, "get", mock_get)
        provider = ArbeitnowProvider({"query": "python", "country": "de"})
        payload = provider.search()
        assert len(payload["data"]) == 1
        assert payload["data"][0]["title"] == "Python Dev"

    def test_search_no_query_returns_all(self, monkeypatch):
        all_data = [{"slug": "1", "title": "Dev", "company_name": "A",
                      "description": "desc", "url": "u", "tags": [],
                      "job_types": [], "created_at": 123, "location": "L"}]

        def mock_get(url, **k):
            resp = requests.Response()
            resp.status_code = 200
            resp._content = __import__("json").dumps({"data": all_data}).encode()
            resp.encoding = "utf-8"
            return resp

        monkeypatch.setattr(requests, "get", mock_get)
        provider = ArbeitnowProvider({"query": "", "country": "de"})
        payload = provider.search()
        assert len(payload["data"]) == 1

    def test_uk_domain_for_gb_country(self, monkeypatch):
        captured_url = {}

        def mock_get(url, **k):
            captured_url["url"] = url
            resp = requests.Response()
            resp.status_code = 200
            resp._content = b'{"data":[]}'
            resp.encoding = "utf-8"
            return resp

        monkeypatch.setattr(requests, "get", mock_get)
        provider = ArbeitnowProvider({"query": "dev", "country": "gb"})
        provider.search()
        assert "co.uk" in captured_url["url"]

    def test_default_domain_for_other_countries(self, monkeypatch):
        captured_url = {}

        def mock_get(url, **k):
            captured_url["url"] = url
            resp = requests.Response()
            resp.status_code = 200
            resp._content = b'{"data":[]}'
            resp.encoding = "utf-8"
            return resp

        monkeypatch.setattr(requests, "get", mock_get)
        provider = ArbeitnowProvider({"query": "dev", "country": "de"})
        provider.search()
        assert "co.uk" not in captured_url["url"]


# ---------------------------------------------------------------------------
# SerpApiProvider
# ---------------------------------------------------------------------------

class TestSerpApiProvider:
    def test_not_configured_without_key(self):
        provider = SerpApiProvider({})
        assert not provider.is_configured()

    def test_is_configured_with_key(self):
        provider = SerpApiProvider({"serpapi_api_key": "fake-key"})
        assert provider.is_configured()

    def test_not_configured_with_none_key(self):
        provider = SerpApiProvider({"serpapi_api_key": None})
        assert not provider.is_configured()

    def test_normalize_canonical_keys(self):
        provider = SerpApiProvider({"serpapi_api_key": "k"})
        jobs = provider.normalize(_serpapi_payload(1))
        assert len(jobs) == 1
        assert set(jobs[0].keys()) == {
            "id", "title", "company", "location", "category",
            "description", "url", "salary", "created", "source",
        }

    def test_source_is_serpapi(self):
        provider = SerpApiProvider({"serpapi_api_key": "k"})
        jobs = provider.normalize(_serpapi_payload(1))
        assert jobs[0]["source"] == "serpapi"

    def test_salary_from_extensions(self):
        provider = SerpApiProvider({"serpapi_api_key": "k"})
        jobs = provider.normalize(_serpapi_payload(1))
        assert jobs[0]["salary"] == "$150,000 - $200,000"

    def test_normalize_invalid_payload(self):
        provider = SerpApiProvider({"serpapi_api_key": "k"})
        assert provider.normalize(None) == []


# ---------------------------------------------------------------------------
# JoobleProvider
# ---------------------------------------------------------------------------

class TestJoobleProvider:
    def test_not_configured_without_key(self):
        provider = JoobleProvider({})
        assert not provider.is_configured()

    def test_is_configured_with_key(self):
        provider = JoobleProvider({"jooble_api_key": "k"})
        assert provider.is_configured()

    def test_not_configured_with_none_key(self):
        provider = JoobleProvider({"jooble_api_key": None})
        assert not provider.is_configured()

    def test_normalize_canonical_keys(self):
        provider = JoobleProvider({"jooble_api_key": "k"})
        jobs = provider.normalize(_jooble_payload(1))
        assert len(jobs) == 1
        assert set(jobs[0].keys()) == {
            "id", "title", "company", "location", "category",
            "description", "url", "salary", "created", "source",
        }

    def test_source_is_jooble(self):
        provider = JoobleProvider({"jooble_api_key": "k"})
        jobs = provider.normalize(_jooble_payload(1))
        assert jobs[0]["source"] == "jooble"

    def test_snippet_as_description(self):
        provider = JoobleProvider({"jooble_api_key": "k"})
        jobs = provider.normalize(_jooble_payload(1))
        assert "Analyze data" in jobs[0]["description"]


# ---------------------------------------------------------------------------
# USAJobsProvider
# ---------------------------------------------------------------------------

class TestUSAJobsProvider:
    def test_not_configured_without_key(self):
        provider = USAJobsProvider({"country": "us"})
        assert not provider.is_configured()

    def test_not_configured_for_non_us(self):
        provider = USAJobsProvider({"country": "br", "usajobs_api_key": "k"})
        assert not provider.is_configured()

    def test_not_configured_with_none_key(self):
        provider = USAJobsProvider({"country": "us", "usajobs_api_key": None})
        assert not provider.is_configured()

    def test_is_configured_us_with_key(self):
        provider = USAJobsProvider({"country": "us", "usajobs_api_key": "k"})
        assert provider.is_configured()

    def test_normalize_canonical_keys(self):
        provider = USAJobsProvider({"country": "us", "usajobs_api_key": "k"})
        jobs = provider.normalize(_usajobs_payload(1))
        assert len(jobs) == 1
        assert set(jobs[0].keys()) == {
            "id", "title", "company", "location", "category",
            "description", "url", "salary", "created", "source",
        }

    def test_source_is_usajobs(self):
        provider = USAJobsProvider({"country": "us", "usajobs_api_key": "k"})
        jobs = provider.normalize(_usajobs_payload(1))
        assert jobs[0]["source"] == "usajobs"

    def test_salary_formatted(self):
        provider = USAJobsProvider({"country": "us", "usajobs_api_key": "k"})
        jobs = provider.normalize(_usajobs_payload(1))
        assert "70000" in jobs[0]["salary"]

    def test_normalize_empty(self):
        provider = USAJobsProvider({"country": "us", "usajobs_api_key": "k"})
        assert provider.normalize({"SearchResult": {"SearchResultItems": []}}) == []

    def test_normalize_invalid(self):
        provider = USAJobsProvider({"country": "us", "usajobs_api_key": "k"})
        assert provider.normalize(None) == []


# ---------------------------------------------------------------------------
# run_cascade — stop at target
# ---------------------------------------------------------------------------

class TestCascadeStopAtTarget:
    def test_stops_when_target_reached(self, monkeypatch):
        calls = []

        def mock_adzuna_search(self, limit=None):
            calls.append("adzuna")
            return _adzuna_payload(10)

        def mock_himalayas_search(self, limit=None):
            calls.append("himalayas")
            return _himalayas_payload(10)

        monkeypatch.setattr(AdzunaProvider, "search", mock_adzuna_search)
        monkeypatch.setattr(HimalayasProvider, "search", mock_himalayas_search)
        monkeypatch.setattr(SerpApiProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(JoobleProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(ArbeitnowProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(USAJobsProvider, "is_configured", lambda self: False)

        config = _adzuna_config()
        result = run_cascade(config, target=5)
        assert len(result["jobs"]) == 5
        assert result["reached_target"] is True
        assert calls == ["adzuna"]

    def test_stops_in_middle_of_provider(self, monkeypatch):
        def mock_adzuna_search(self, limit=None):
            return _adzuna_payload(3)

        def mock_himalayas_search(self, limit=None):
            return _himalayas_payload(5)

        monkeypatch.setattr(AdzunaProvider, "search", mock_adzuna_search)
        monkeypatch.setattr(HimalayasProvider, "search", mock_himalayas_search)
        monkeypatch.setattr(SerpApiProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(JoobleProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(ArbeitnowProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(USAJobsProvider, "is_configured", lambda self: False)

        config = _adzuna_config()
        result = run_cascade(config, target=5)
        assert len(result["jobs"]) == 5
        assert result["coverage"].get("adzuna", 0) == 3
        assert result["coverage"].get("himalayas", 0) == 2
        assert result["reached_target"] is True


# ---------------------------------------------------------------------------
# run_cascade — provider order
# ---------------------------------------------------------------------------

class TestCascadeOrder:
    def test_follows_cascade_order(self, monkeypatch):
        order = []

        def track_adzuna(self, limit=None):
            order.append("adzuna")
            return _adzuna_payload(1)

        def track_himalayas(self, limit=None):
            order.append("himalayas")
            return _himalayas_payload(1)

        def track_arbeitnow(self, limit=None):
            order.append("arbeitnow")
            return _arbeitnow_payload(1)

        monkeypatch.setattr(AdzunaProvider, "search", track_adzuna)
        monkeypatch.setattr(HimalayasProvider, "search", track_himalayas)
        monkeypatch.setattr(ArbeitnowProvider, "search", track_arbeitnow)
        monkeypatch.setattr(SerpApiProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(JoobleProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(USAJobsProvider, "is_configured", lambda self: False)

        result = run_cascade(_adzuna_config(), target=10)
        assert order == ["adzuna", "himalayas", "arbeitnow"]
        assert len(result["jobs"]) == 3


# ---------------------------------------------------------------------------
# run_cascade — skip without key
# ---------------------------------------------------------------------------

class TestCascadeSkipWithoutKey:
    def test_adzuna_skipped_without_key(self, monkeypatch):
        himalayas_called = []

        def track_himalayas(self, limit=None):
            himalayas_called.append(True)
            return _himalayas_payload(2)

        monkeypatch.setattr(HimalayasProvider, "search", track_himalayas)
        monkeypatch.setattr(SerpApiProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(JoobleProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(ArbeitnowProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(USAJobsProvider, "is_configured", lambda self: False)

        config = {"adzuna_app_id": "", "adzuna_app_key": "", "query": "python", "country": "br"}
        result = run_cascade(config, target=5)
        assert len(himalayas_called) == 1
        assert "adzuna" not in result["calls"]
        assert "himalayas" in result["coverage"]

    def test_keyless_providers_always_run(self, monkeypatch):
        run_sources = []

        def track_himalayas(self, limit=None):
            run_sources.append("himalayas")
            return _himalayas_payload(1)

        def track_arbeitnow(self, limit=None):
            run_sources.append("arbeitnow")
            return _arbeitnow_payload(1)

        monkeypatch.setattr(HimalayasProvider, "search", track_himalayas)
        monkeypatch.setattr(ArbeitnowProvider, "search", track_arbeitnow)
        monkeypatch.setattr(AdzunaProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(SerpApiProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(JoobleProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(USAJobsProvider, "is_configured", lambda self: False)

        result = run_cascade({"query": "dev"}, target=5)
        assert "himalayas" in run_sources
        assert "arbeitnow" in run_sources


# ---------------------------------------------------------------------------
# run_cascade — partial failure
# ---------------------------------------------------------------------------

class TestCascadePartialFailure:
    def test_failure_does_not_abort(self, monkeypatch):
        def boom_adzuna(self, limit=None):
            raise ProviderRequestError("timeout")

        def ok_himalayas(self, limit=None):
            return _himalayas_payload(3)

        monkeypatch.setattr(AdzunaProvider, "search", boom_adzuna)
        monkeypatch.setattr(HimalayasProvider, "search", ok_himalayas)
        monkeypatch.setattr(SerpApiProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(JoobleProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(ArbeitnowProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(USAJobsProvider, "is_configured", lambda self: False)

        result = run_cascade(_adzuna_config(), target=10)
        assert len(result["jobs"]) == 3
        assert result["errors"]["adzuna"] == "timeout"
        assert result["coverage"].get("himalayas", 0) == 3
        assert result["calls"].get("adzuna", 0) == 1

    def test_second_provider_also_fails(self, monkeypatch):
        def boom_adzuna(self, limit=None):
            raise ProviderRequestError("http 500", status_code=500)

        def boom_himalayas(self, limit=None):
            raise ConnectionError("network down")

        monkeypatch.setattr(AdzunaProvider, "search", boom_adzuna)
        monkeypatch.setattr(HimalayasProvider, "search", boom_himalayas)
        monkeypatch.setattr(SerpApiProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(JoobleProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(ArbeitnowProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(USAJobsProvider, "is_configured", lambda self: False)

        result = run_cascade(_adzuna_config(), target=10)
        assert result["jobs"] == []
        assert "adzuna" in result["errors"]
        assert "himalayas" in result["errors"]
        assert result["reached_target"] is False

    def test_is_configured_raising_does_not_abort(self, monkeypatch):
        def boom_himalayas(self, limit=None):
            return _himalayas_payload(2)

        def failing_is_configured(self):
            raise RuntimeError("config bug")

        monkeypatch.setattr(AdzunaProvider, "is_configured", failing_is_configured)
        monkeypatch.setattr(HimalayasProvider, "search", boom_himalayas)
        monkeypatch.setattr(SerpApiProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(JoobleProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(ArbeitnowProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(USAJobsProvider, "is_configured", lambda self: False)

        result = run_cascade(_adzuna_config(), target=4)
        assert len(result["jobs"]) == 2
        assert "RuntimeError: config bug" in result["errors"]["adzuna"]
        assert result["coverage"].get("himalayas", 0) == 2


# ---------------------------------------------------------------------------
# run_cascade — total failure
# ---------------------------------------------------------------------------

class TestCascadeTotalFailure:
    def test_all_fail_returns_empty(self, monkeypatch):
        def boom(self, limit=None):
            raise ProviderRequestError("timeout")

        monkeypatch.setattr(AdzunaProvider, "search", boom)
        monkeypatch.setattr(HimalayasProvider, "search", boom)
        monkeypatch.setattr(SerpApiProvider, "search", boom)
        monkeypatch.setattr(JoobleProvider, "search", boom)
        monkeypatch.setattr(ArbeitnowProvider, "search", boom)
        monkeypatch.setattr(USAJobsProvider, "search", boom)
        monkeypatch.setattr(SerpApiProvider, "is_configured", lambda self: True)
        monkeypatch.setattr(JoobleProvider, "is_configured", lambda self: True)
        monkeypatch.setattr(USAJobsProvider, "is_configured", lambda self: True)

        config = _adzuna_config()
        config["serpapi_api_key"] = "k"
        config["jooble_api_key"] = "k"
        config["usajobs_api_key"] = "k"
        result = run_cascade(config, target=10)
        assert result["jobs"] == []
        assert len(result["errors"]) == 6
        assert result["reached_target"] is False

    def test_all_skipped_returns_empty(self, monkeypatch):
        monkeypatch.setattr(AdzunaProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(HimalayasProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(SerpApiProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(JoobleProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(ArbeitnowProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(USAJobsProvider, "is_configured", lambda self: False)

        config = {"query": "dev"}
        result = run_cascade(config, target=10)
        assert result["jobs"] == []
        assert result["reached_target"] is False


# ---------------------------------------------------------------------------
# run_cascade — dedup between sources
# ---------------------------------------------------------------------------

class TestCascadeDedup:
    def test_duplicate_skipped(self, monkeypatch):
        dup_job = {
            "slug": "same-job",
            "title": "Python Dev",
            "company_name": "SameCorp",
            "description": "desc",
            "url": "https://example.com",
            "tags": [],
            "job_types": [],
            "created_at": 123,
            "location": "Berlin",
        }
        unique_job = {
            "slug": "unique-job",
            "title": "Java Dev",
            "company_name": "OtherCorp",
            "description": "desc2",
            "url": "https://example.com/2",
            "tags": [],
            "job_types": [],
            "created_at": 456,
            "location": "Munich",
        }

        def mock_adzuna(self, limit=None):
            return {"results": [{
                "id": "same-job", "title": "Python Dev",
                "company": {"display_name": "SameCorp"},
                "location": {"display_name": "Berlin"},
                "category": {"display_name": "IT"},
                "description": "desc",
                "redirect_url": "https://example.com",
                "salary_min": None, "salary_max": None,
                "created": "2026-09-01",
            }], "count": 1}

        call_count = [0]

        def mock_himalayas(self, limit=None):
            if call_count[0] == 0:
                call_count[0] += 1
                return {
                    "totalCount": 2,
                    "jobs": [{
                        "title": "Python Dev",
                        "companyName": "SameCorp",
                        "locationRestrictions": ["Berlin"],
                        "categories": ["IT"],
                        "description": "desc",
                        "applicationLink": "https://example.com",
                        "guid": "h1",
                    }, {
                        "title": "Java Dev",
                        "companyName": "OtherCorp",
                        "locationRestrictions": ["Munich"],
                        "categories": ["IT"],
                        "description": "desc2",
                        "applicationLink": "https://example.com/2",
                        "guid": "h2",
                    }],
                }
            return {"totalCount": 0, "jobs": []}

        monkeypatch.setattr(AdzunaProvider, "search", mock_adzuna)
        monkeypatch.setattr(HimalayasProvider, "search", mock_himalayas)
        monkeypatch.setattr(SerpApiProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(JoobleProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(ArbeitnowProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(USAJobsProvider, "is_configured", lambda self: False)

        result = run_cascade(_adzuna_config(), target=10)
        assert len(result["jobs"]) == 2
        assert result["coverage"].get("adzuna", 0) == 1
        assert result["coverage"].get("himalayas", 0) == 1

    def test_duplicate_with_accents_deduped(self, monkeypatch):
        def mock_adzuna(self, limit=None):
            return {"results": [{
                "id": "a1", "title": "Engenheiro de Software",
                "company": {"display_name": "Ação Empresa"},
                "location": {"display_name": "São Paulo"},
                "category": {"display_name": "IT"},
                "description": "first",
                "redirect_url": "https://a.com/1",
                "salary_min": None, "salary_max": None,
                "created": "2026-09-01",
            }], "count": 1}

        def mock_himalayas(self, limit=None):
            return {
                "totalCount": 1,
                "jobs": [{
                    "title": "Engenheiro de Software",
                    "companyName": "Acao Empresa",
                    "locationRestrictions": ["Sao Paulo"],
                    "categories": ["IT"],
                    "description": "duplicate",
                    "applicationLink": "https://h.com/1",
                    "guid": "h1",
                }],
            }

        monkeypatch.setattr(AdzunaProvider, "search", mock_adzuna)
        monkeypatch.setattr(HimalayasProvider, "search", mock_himalayas)
        monkeypatch.setattr(SerpApiProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(JoobleProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(ArbeitnowProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(USAJobsProvider, "is_configured", lambda self: False)

        result = run_cascade(_adzuna_config(), target=10)
        assert len(result["jobs"]) == 1
        assert result["jobs"][0]["source"] == "adzuna"
        assert result["coverage"].get("adzuna", 0) == 1
        assert result["coverage"].get("himalayas", 0) == 0

    def test_first_source_wins(self, monkeypatch):
        def mock_adzuna(self, limit=None):
            return {"results": [{
                "id": "a1", "title": "Shared Job",
                "company": {"display_name": "Corp"},
                "location": {"display_name": "Berlin"},
                "category": {"display_name": "IT"},
                "description": "first",
                "redirect_url": "https://a.com/1",
                "salary_min": None, "salary_max": None,
                "created": "2026-09-01",
            }], "count": 1}

        def mock_himalayas(self, limit=None):
            return {
                "totalCount": 1,
                "jobs": [{
                    "title": "Shared Job",
                    "companyName": "Corp",
                    "locationRestrictions": ["Berlin"],
                    "description": "duplicate",
                    "applicationLink": "https://h.com/1",
                    "guid": "h-dup",
                }],
            }

        monkeypatch.setattr(AdzunaProvider, "search", mock_adzuna)
        monkeypatch.setattr(HimalayasProvider, "search", mock_himalayas)
        monkeypatch.setattr(SerpApiProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(JoobleProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(ArbeitnowProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(USAJobsProvider, "is_configured", lambda self: False)

        result = run_cascade(_adzuna_config(), target=10)
        assert len(result["jobs"]) == 1
        assert result["jobs"][0]["source"] == "adzuna"
        assert result["coverage"].get("adzuna", 0) == 1
        assert result["coverage"].get("himalayas", 0) == 0

    def test_dedup_whitespace_case_insensitive(self, monkeypatch):
        def mock_adzuna(self, limit=None):
            return {"results": [{
                "id": "a1", "title": "  Python  Dev  ",
                "company": {"display_name": "  Corp  "},
                "location": {"display_name": "Berlin"},
                "category": {"display_name": "IT"},
                "description": "d1",
                "redirect_url": "https://a.com/1",
                "salary_min": None, "salary_max": None,
                "created": "2026-09-01",
            }], "count": 1}

        def mock_himalayas(self, limit=None):
            return {
                "totalCount": 1,
                "jobs": [{
                    "title": "python dev",
                    "companyName": "corp",
                    "locationRestrictions": ["Berlin"],
                    "description": "d2",
                    "applicationLink": "https://h.com/1",
                    "guid": "h-dup",
                }],
            }

        monkeypatch.setattr(AdzunaProvider, "search", mock_adzuna)
        monkeypatch.setattr(HimalayasProvider, "search", mock_himalayas)
        monkeypatch.setattr(SerpApiProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(JoobleProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(ArbeitnowProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(USAJobsProvider, "is_configured", lambda self: False)

        result = run_cascade(_adzuna_config(), target=10)
        assert len(result["jobs"]) == 1
        assert result["jobs"][0]["source"] == "adzuna"


# ---------------------------------------------------------------------------
# run_cascade — coverage, calls, errors metadata
# ---------------------------------------------------------------------------

class TestCascadeMetadata:
    def test_calls_count_only_attempted(self, monkeypatch):
        def boom(self, limit=None):
            raise ProviderRequestError("timeout")

        def ok(self, limit=None):
            return _himalayas_payload(2)

        monkeypatch.setattr(AdzunaProvider, "search", boom)
        monkeypatch.setattr(HimalayasProvider, "search", ok)
        monkeypatch.setattr(SerpApiProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(JoobleProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(ArbeitnowProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(USAJobsProvider, "is_configured", lambda self: False)

        result = run_cascade(_adzuna_config(), target=10)
        assert result["calls"]["adzuna"] == 1
        assert result["calls"]["himalayas"] == 1

    def test_errors_not_empty_on_failure(self, monkeypatch):
        def boom(self, limit=None):
            raise ProviderRequestError("http 429", status_code=429)

        monkeypatch.setattr(AdzunaProvider, "search", boom)
        monkeypatch.setattr(HimalayasProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(SerpApiProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(JoobleProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(ArbeitnowProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(USAJobsProvider, "is_configured", lambda self: False)

        config = _adzuna_config()
        result = run_cascade(config, target=10)
        assert result["errors"]["adzuna"] == "http 429"

    def test_no_leaked_keys_in_errors(self, monkeypatch):
        def boom(self, limit=None):
            raise ProviderRequestError("request failed")

        monkeypatch.setattr(AdzunaProvider, "search", boom)
        monkeypatch.setattr(HimalayasProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(SerpApiProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(JoobleProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(ArbeitnowProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(USAJobsProvider, "is_configured", lambda self: False)

        result = run_cascade(_adzuna_config(), target=10)
        for msg in result["errors"].values():
            assert "app-id" not in msg
            assert "app-key" not in msg
            assert "app_id" not in msg
            assert "api_key" not in msg

    def test_coverage_counts_only_unique(self, monkeypatch):
        def mock_adzuna(self, limit=None):
            return {"results": [
                {"id": "1", "title": "Job A", "company": {"display_name": "C"},
                 "location": {"display_name": "L"}, "category": {"display_name": "IT"},
                 "description": "d", "redirect_url": "u", "salary_min": None,
                 "salary_max": None, "created": "2026-09-01"},
                {"id": "2", "title": "Job B", "company": {"display_name": "C"},
                 "location": {"display_name": "L"}, "category": {"display_name": "IT"},
                 "description": "d2", "redirect_url": "u2", "salary_min": None,
                 "salary_max": None, "created": "2026-09-02"},
            ], "count": 2}

        def mock_himalayas(self, limit=None):
            return {"totalCount": 1, "jobs": [{
                "title": "Job B",
                "companyName": "C",
                "locationRestrictions": ["L"],
                "description": "dup",
                "applicationLink": "u-dup",
                "guid": "h-dup",
            }]}

        monkeypatch.setattr(AdzunaProvider, "search", mock_adzuna)
        monkeypatch.setattr(HimalayasProvider, "search", mock_himalayas)
        monkeypatch.setattr(SerpApiProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(JoobleProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(ArbeitnowProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(USAJobsProvider, "is_configured", lambda self: False)

        result = run_cascade(_adzuna_config(), target=10)
        assert result["coverage"]["adzuna"] == 2
        assert result["coverage"].get("himalayas", 0) == 0

    def test_result_shape(self, monkeypatch):
        monkeypatch.setattr(AdzunaProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(HimalayasProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(SerpApiProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(JoobleProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(ArbeitnowProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(USAJobsProvider, "is_configured", lambda self: False)

        result = run_cascade({"query": "dev"}, target=5)
        assert set(result.keys()) == {"jobs", "coverage", "calls", "errors", "reached_target"}


# ---------------------------------------------------------------------------
# run_cascade — target = 0
# ---------------------------------------------------------------------------

class TestCascadeEdgeCases:
    def test_target_zero_returns_empty(self, monkeypatch):
        result = run_cascade(_adzuna_config(), target=0)
        assert result["jobs"] == []
        assert result["reached_target"] is True

    def test_no_providers_configured(self, monkeypatch):
        monkeypatch.setattr(AdzunaProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(HimalayasProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(SerpApiProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(JoobleProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(ArbeitnowProvider, "is_configured", lambda self: False)
        monkeypatch.setattr(USAJobsProvider, "is_configured", lambda self: False)

        result = run_cascade({"query": "dev"}, target=5)
        assert result["jobs"] == []
        assert result["reached_target"] is False
