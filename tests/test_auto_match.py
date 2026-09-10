"""Tests for the auto_match service layer (Adzuna + AI calls are mocked)."""

import pytest
import requests

import auto_match
from auto_match import run_auto_match

# --------------------------------------------------------------------------
# Test doubles
# --------------------------------------------------------------------------


def _make_job(index: int, url: str = "https://example.com/job") -> dict:
    """Build a normalized job dict exactly as job_search.fetch_jobs returns it."""
    return {
        "id": str(index),
        "title": f"Job {index}",
        "company": f"Company {index}",
        "location": "Sao Paulo",
        "category": "IT Jobs",
        "description": f"Snippet {index} with a short adzuna description.",
        "url": url,
        "salary": "R$ 5.000",
        "created": "2026-09-01",
    }


def _analysis(score) -> dict:
    """Build a valid raw AI response dict for a given score."""
    return {
        "overall_score": score,
        "pontos_fortes": ["Python", "FastAPI"],
        "lacunas": ["Kubernetes"],
        "sugestoes_melhoria": ["Add metrics to resume"],
        "keyword_analysis": {
            "matched_keywords": [{"keyword": "python", "category": "hard_skill"}],
            "missing_keywords": [],
        },
    }


def _run(**overrides) -> dict:
    """Call run_auto_match with full valid defaults, overriding as needed."""
    params = {
        "profile_text": "Python developer with FastAPI and Docker experience.",
        "keyword": "python developer",
        "location": "Sao Paulo",
        "country": "br",
        "results_per_page": 10,
        "threshold": 60,
        "adzuna_app_id": "app-id",
        "adzuna_app_key": "app-key",
        "ai_api_key": "ai-key",
        "ai_provider": "opencode_zen",
        "ai_model": "big-pickle",
        "language": "English",
    }
    params.update(overrides)
    return run_auto_match(**params)


# --------------------------------------------------------------------------
# Input validation (RN-05)
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "override,message",
    [
        ({"profile_text": "   "}, "Profile text"),
        ({"profile_text": ""}, "Profile text"),
        ({"keyword": ""}, "keyword"),
        ({"keyword": "   "}, "keyword"),
        ({"adzuna_app_id": "", "adzuna_app_key": "k"}, "Adzuna"),
        ({"adzuna_app_id": "i", "adzuna_app_key": " "}, "Adzuna"),
        ({"ai_api_key": ""}, "AI provider"),
        ({"ai_api_key": "  "}, "AI provider"),
    ],
)
def test_missing_required_inputs_raise_valueerror(override, message):
    with pytest.raises(ValueError, match=message):
        _run(**override)


# --------------------------------------------------------------------------
# Happy path (RN-02 / RN-03 / RN-11)
# --------------------------------------------------------------------------

def test_happy_path_fetched_jd_matched_and_below(monkeypatch):
    jobs = [_make_job(1), _make_job(2), _make_job(3)]
    scores = iter([85, 45, 72])
    captured = []

    def fake_analyze(profile_text, job_description, provider, model, prompt, language, **kw):
        captured.append(
            {
                "jd": job_description,
                "prompt": prompt,
                "language": language,
                "api_key": kw.get("api_key"),
                "provider": provider,
                "model": model,
            }
        )
        return _analysis(next(scores))

    monkeypatch.setattr(auto_match, "fetch_jobs", lambda *a, **k: (jobs, len(jobs)))
    monkeypatch.setattr(auto_match, "fetch_job_description", lambda url: f"Full JD for {url}")
    monkeypatch.setattr(auto_match, "analyze_profile", fake_analyze)

    result = _run()

    statuses = [r["status"] for r in result["results"]]
    assert statuses == ["matched", "below_threshold", "matched"]
    assert result["total_found"] == 3
    assert result["total_analyzed"] == 3
    assert result["total_matched"] == 2
    assert result["total_below_threshold"] == 1
    assert result["total_failed"] == 0

    for res in result["results"]:
        assert res["job"]["jd_source"] == "fetched"
        assert res["job"]["full_description"].startswith("Full JD for")
        assert isinstance(res["analysis"]["overall_score"], int)
        assert res["analysis"]["pontos_fortes"] == ["Python", "FastAPI"]
        assert res["analysis"]["keyword_analysis"]["matched_keywords"][0]["keyword"] == "python"

    first = captured[0]
    assert first["jd"] == "Full JD for https://example.com/job"
    assert first["prompt"] is auto_match.ANALYSIS_PROMPT
    assert first["language"] == "English"
    assert first["api_key"] == "ai-key"
    assert first["provider"] == "opencode_zen"
    assert first["model"] == "big-pickle"


def test_result_contract_shape(monkeypatch):
    monkeypatch.setattr(auto_match, "fetch_jobs", lambda *a, **k: ([_make_job(1)], 1))
    monkeypatch.setattr(auto_match, "fetch_job_description", lambda url: "Full JD text here")
    monkeypatch.setattr(auto_match, "analyze_profile", lambda *a, **k: _analysis(77))

    res = _run()["results"][0]

    assert set(res) == {"job", "analysis", "status"}
    assert set(res["job"]) == {
        "id", "title", "company", "location", "category",
        "description", "full_description", "url", "salary", "created", "jd_source",
    }
    assert set(res["analysis"]) == {
        "overall_score", "pontos_fortes", "lacunas", "sugestoes_melhoria", "keyword_analysis",
    }
    assert res["status"] in {"matched", "below_threshold", "failed", "no_url", "no_jd"}


def test_no_jobs_returns_empty_summary(monkeypatch):
    monkeypatch.setattr(auto_match, "fetch_jobs", lambda *a, **k: ([], 0))
    result = _run()
    assert result["results"] == []
    assert result["total_found"] == 0
    assert result["total_analyzed"] == 0
    assert result["total_matched"] == 0
    assert result["total_below_threshold"] == 0
    assert result["total_failed"] == 0


# --------------------------------------------------------------------------
# Threshold behavior (RN-01 / RN-03)
# --------------------------------------------------------------------------

def test_threshold_clamped_high_bounds(monkeypatch):
    monkeypatch.setattr(auto_match, "fetch_jobs", lambda *a, **k: ([_make_job(1)], 1))
    monkeypatch.setattr(auto_match, "fetch_job_description", lambda url: "Full JD")
    monkeypatch.setattr(auto_match, "analyze_profile", lambda *a, **k: _analysis(85))

    result = _run(threshold=95)  # clamped to 90 → 85 is below
    assert result["results"][0]["status"] == "below_threshold"
    assert result["total_below_threshold"] == 1


def test_threshold_clamped_low_bounds(monkeypatch):
    monkeypatch.setattr(auto_match, "fetch_jobs", lambda *a, **k: ([_make_job(1)], 1))
    monkeypatch.setattr(auto_match, "fetch_job_description", lambda url: "Full JD")
    monkeypatch.setattr(auto_match, "analyze_profile", lambda *a, **k: _analysis(20))

    result = _run(threshold=10)  # clamped to 30 → 20 is below
    assert result["results"][0]["status"] == "below_threshold"

    monkeypatch.setattr(auto_match, "analyze_profile", lambda *a, **k: _analysis(30))
    result = _run(threshold=10)
    assert result["results"][0]["status"] == "matched"


# --------------------------------------------------------------------------
# Adzuna limits (RN-04)
# --------------------------------------------------------------------------

def test_results_per_page_clamped_to_max(monkeypatch):
    captured = {}

    def fake_fetch_jobs(query, location, country, results_per_page, app_id, app_key):
        captured.update(locals())
        return ([_make_job(1)], 1)

    monkeypatch.setattr(auto_match, "fetch_jobs", fake_fetch_jobs)
    monkeypatch.setattr(auto_match, "fetch_job_description", lambda url: "Full JD")
    monkeypatch.setattr(auto_match, "analyze_profile", lambda *a, **k: _analysis(90))

    _run(results_per_page=500)
    assert captured["results_per_page"] == 50

    _run(results_per_page=0)
    assert captured["results_per_page"] == 1

    _run(results_per_page=25)
    assert captured["results_per_page"] == 25


def test_fetch_jobs_receives_keyword_and_keys(monkeypatch):
    captured = {}

    def fake_fetch_jobs(query, location, country, results_per_page, app_id, app_key):
        captured.update(locals())
        return ([_make_job(1)], 1)

    monkeypatch.setattr(auto_match, "fetch_jobs", fake_fetch_jobs)
    monkeypatch.setattr(auto_match, "fetch_job_description", lambda url: "Full JD")
    monkeypatch.setattr(auto_match, "analyze_profile", lambda *a, **k: _analysis(90))

    _run(location="", country="us")
    assert captured["query"] == "python developer"
    assert captured["location"] == ""
    assert captured["country"] == "us"
    assert captured["app_id"] == "app-id"
    assert captured["app_key"] == "app-key"


# --------------------------------------------------------------------------
# JD sourcing (RN-11)
# --------------------------------------------------------------------------

def test_no_url_job_skipped_without_analysis(monkeypatch):
    jobs = [_make_job(1, url=""), _make_job(2, url="https://example.com/job2")]
    fetch_calls = []
    analyze_calls = []

    monkeypatch.setattr(auto_match, "fetch_jobs", lambda *a, **k: (jobs, 2))
    monkeypatch.setattr(
        auto_match,
        "fetch_job_description",
        lambda url: fetch_calls.append(url) or "Full JD",
    )
    monkeypatch.setattr(auto_match, "analyze_profile", lambda *a, **k: analyze_calls.append(1) or _analysis(80))

    result = _run()
    first, second = result["results"]

    assert first["status"] == "no_url"
    assert first["analysis"] is None
    assert first["job"]["jd_source"] == "empty"
    assert first["job"]["full_description"] == ""

    assert second["status"] == "matched"
    assert fetch_calls == ["https://example.com/job2"]
    assert len(analyze_calls) == 1
    assert result["total_failed"] == 1
    assert result["total_analyzed"] == 1


def test_empty_jd_fetch_falls_back_to_snippet(monkeypatch):
    jobs = [_make_job(1)]
    captured = {}

    def fake_analyze(profile_text, job_description, provider, model, prompt, language, **kw):
        captured["jd"] = job_description
        return _analysis(70)

    monkeypatch.setattr(auto_match, "fetch_jobs", lambda *a, **k: (jobs, 1))
    monkeypatch.setattr(auto_match, "fetch_job_description", lambda url: "")
    monkeypatch.setattr(auto_match, "analyze_profile", fake_analyze)

    res = _run()["results"][0]

    assert res["status"] == "matched"
    assert res["job"]["jd_source"] == "snippet"
    assert res["job"]["full_description"] == ""
    assert captured["jd"] == jobs[0]["description"]


def test_failed_jd_fetch_falls_back_to_snippet(monkeypatch):
    def boom(url):
        raise requests.RequestException("site blocked automated access")

    monkeypatch.setattr(auto_match, "fetch_jobs", lambda *a, **k: ([_make_job(1)], 1))
    monkeypatch.setattr(auto_match, "fetch_job_description", boom)
    monkeypatch.setattr(auto_match, "analyze_profile", lambda *a, **k: _analysis(70))

    res = _run()["results"][0]

    assert res["status"] == "matched"
    assert res["job"]["jd_source"] == "snippet"


def test_no_jd_marks_job_when_snippet_also_empty(monkeypatch):
    job = _make_job(1)
    job["description"] = "   "
    analyze_calls = []

    monkeypatch.setattr(auto_match, "fetch_jobs", lambda *a, **k: ([job], 1))
    monkeypatch.setattr(auto_match, "fetch_job_description", lambda url: "")
    monkeypatch.setattr(auto_match, "analyze_profile", lambda *a, **k: analyze_calls.append(1) or _analysis(80))

    res = _run()["results"][0]

    assert res["status"] == "no_jd"
    assert res["analysis"] is None
    assert res["job"]["jd_source"] == "empty"
    assert analyze_calls == []


# --------------------------------------------------------------------------
# AI failures (RN-06, 429, JSON parse, missing score)
# --------------------------------------------------------------------------

def test_ai_exception_marks_failed_and_batch_continues(monkeypatch):
    calls = []

    def boom(*args, **kwargs):
        calls.append(1)
        raise RuntimeError("429 rate limit exceeded")

    monkeypatch.setattr(auto_match, "fetch_jobs", lambda *a, **k: ([_make_job(1), _make_job(2)], 2))
    monkeypatch.setattr(auto_match, "fetch_job_description", lambda url: "Full JD")
    monkeypatch.setattr(auto_match, "analyze_profile", boom)

    result = _run()

    assert len(calls) == 4  # 2 jobs × 2 attempts (transient 429 retried once)
    assert all(r["status"] == "failed" for r in result["results"])
    assert result["total_failed"] == 2
    assert result["total_analyzed"] == 2


def test_transient_ai_failure_retries_once(monkeypatch):
    calls = []

    def flaky(*args, **kwargs):
        calls.append(1)
        raise RuntimeError("429 rate limit exceeded")

    monkeypatch.setattr(auto_match, "fetch_jobs", lambda *a, **k: ([_make_job(1)], 1))
    monkeypatch.setattr(auto_match, "fetch_job_description", lambda url: "Full JD")
    monkeypatch.setattr(auto_match, "analyze_profile", flaky)

    res = _run()["results"][0]
    assert res["status"] == "failed"
    assert len(calls) == 2  # exactly one retry, then give up


def test_non_transient_ai_failure_does_not_retry(monkeypatch):
    calls = []

    def broken(*args, **kwargs):
        calls.append(1)
        raise ValueError("model not supported")

    monkeypatch.setattr(auto_match, "fetch_jobs", lambda *a, **k: ([_make_job(1)], 1))
    monkeypatch.setattr(auto_match, "fetch_job_description", lambda url: "Full JD")
    monkeypatch.setattr(auto_match, "analyze_profile", broken)

    res = _run()["results"][0]
    assert res["status"] == "failed"
    assert len(calls) == 1  # non-transient, no retry


def test_adzuna_failure_raises_friendly_valueerror(monkeypatch):
    def broken(*args, **kwargs):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(auto_match, "fetch_jobs", broken)

    with pytest.raises(ValueError) as excinfo:
        _run()
    assert "Adzuna" in str(excinfo.value)


def test_score_equal_to_threshold_is_matched(monkeypatch):
    monkeypatch.setattr(auto_match, "fetch_jobs", lambda *a, **k: ([_make_job(1)], 1))
    monkeypatch.setattr(auto_match, "fetch_job_description", lambda url: "Full JD")
    monkeypatch.setattr(
        auto_match, "analyze_profile", lambda *a, **k: _analysis(60)
    )

    res = _run()["results"][0]
    assert res["status"] == "matched"  # boundary: score == threshold counts as match
    assert res["analysis"]["overall_score"] == 60


def test_ai_non_dict_result_marks_failed(monkeypatch):
    monkeypatch.setattr(auto_match, "fetch_jobs", lambda *a, **k: ([_make_job(1)], 1))
    monkeypatch.setattr(auto_match, "fetch_job_description", lambda url: "Full JD")
    monkeypatch.setattr(auto_match, "analyze_profile", lambda *a, **k: ["not", "a", "dict"])

    res = _run()["results"][0]
    assert res["status"] == "failed"
    assert res["analysis"] is None
    assert res["job"]["jd_source"] == "fetched"


@pytest.mark.parametrize("raw", [{"pontos_fortes": []}, {"overall_score": None}, {"overall_score": "abc"}])
def test_ai_missing_or_invalid_score_marks_failed(monkeypatch, raw):
    monkeypatch.setattr(auto_match, "fetch_jobs", lambda *a, **k: ([_make_job(1)], 1))
    monkeypatch.setattr(auto_match, "fetch_job_description", lambda url: "Full JD")
    monkeypatch.setattr(auto_match, "analyze_profile", lambda *a, **k: raw)

    res = _run()["results"][0]
    assert res["status"] == "failed"
    assert res["analysis"] is None


# --------------------------------------------------------------------------
# Score normalization
# --------------------------------------------------------------------------

def test_score_float_coerced_to_int_and_analysis_sliced(monkeypatch):
    def fake_analyze(*args, **kwargs):
        return {
            "overall_score": "85.6",
            "pontos_fortes": [f"strength {i}" for i in range(5)],
            "lacunas": [f"gap {i}" for i in range(5)],
            "sugestoes_melhoria": ["do more", "add numbers"],
            "keyword_analysis": {"matched_keywords": [], "missing_keywords": []},
        }

    monkeypatch.setattr(auto_match, "fetch_jobs", lambda *a, **k: ([_make_job(1)], 1))
    monkeypatch.setattr(auto_match, "fetch_job_description", lambda url: "Full JD")
    monkeypatch.setattr(auto_match, "analyze_profile", fake_analyze)

    analysis = _run()["results"][0]["analysis"]

    assert analysis["overall_score"] == 85
    assert analysis["pontos_fortes"] == ["strength 0", "strength 1", "strength 2"]
    assert analysis["lacunas"] == ["gap 0", "gap 1", "gap 2"]
    assert analysis["sugestoes_melhoria"] == ["do more", "add numbers"]
    assert analysis["keyword_analysis"] == {"matched_keywords": [], "missing_keywords": []}


def test_score_clamped_to_0_100(monkeypatch):
    scores = iter([150, -5])

    def fake_analyze(*args, **kwargs):
        return {"overall_score": next(scores)}

    monkeypatch.setattr(auto_match, "fetch_jobs", lambda *a, **k: ([_make_job(1), _make_job(2)], 2))
    monkeypatch.setattr(auto_match, "fetch_job_description", lambda url: "Full JD")
    monkeypatch.setattr(auto_match, "analyze_profile", fake_analyze)

    result = _run()
    statuses = [r["status"] for r in result["results"]]
    assert statuses == ["matched", "below_threshold"]
    assert result["results"][0]["analysis"]["overall_score"] == 100
    assert result["results"][1]["analysis"]["overall_score"] == 0

    monkeypatch.setattr(auto_match, "analyze_profile", lambda *a, **k: {"overall_score": 300})
    result = _run()
    assert result["results"][0]["analysis"]["overall_score"] == 100
    assert result["results"][0]["status"] == "matched"


def test_minimal_analysis_filled_with_defaults(monkeypatch):
    monkeypatch.setattr(auto_match, "fetch_jobs", lambda *a, **k: ([_make_job(1)], 1))
    monkeypatch.setattr(auto_match, "fetch_job_description", lambda url: "Full JD")
    monkeypatch.setattr(auto_match, "analyze_profile", lambda *a, **k: {"overall_score": 80})

    analysis = _run()["results"][0]["analysis"]

    assert analysis["pontos_fortes"] == []
    assert analysis["lacunas"] == []
    assert analysis["sugestoes_melhoria"] == []
    assert "keyword_analysis" not in analysis


# --------------------------------------------------------------------------
# Summary counts across mixed statuses
# --------------------------------------------------------------------------

def test_summary_counts_mixed_statuses(monkeypatch):
    jobs = [_make_job(1), _make_job(2), _make_job(3), _make_job(4)]
    jobs[2]["url"] = ""  # no_url
    scores = iter([90, 40])

    def fake_analyze(*args, **kwargs):
        try:
            return _analysis(next(scores))
        except StopIteration:
            raise RuntimeError("model overloaded")

    monkeypatch.setattr(auto_match, "fetch_jobs", lambda *a, **k: (jobs, 4))
    monkeypatch.setattr(auto_match, "fetch_job_description", lambda url: "Full JD")
    monkeypatch.setattr(auto_match, "analyze_profile", fake_analyze)

    result = _run()

    assert [r["status"] for r in result["results"]] == ["matched", "below_threshold", "no_url", "failed"]
    assert result["total_found"] == 4
    assert result["total_analyzed"] == 3
    assert result["total_matched"] == 1
    assert result["total_below_threshold"] == 1
    assert result["total_failed"] == 2


# --------------------------------------------------------------------------
# Progress callback
# --------------------------------------------------------------------------

def test_progress_callback_reports_each_job(monkeypatch):
    jobs = [_make_job(1, url="https://a.com/1"), _make_job(2, url="https://a.com/2")]

    monkeypatch.setattr(auto_match, "fetch_jobs", lambda *a, **k: (jobs, 2))
    monkeypatch.setattr(auto_match, "fetch_job_description", lambda url: "Full JD")
    monkeypatch.setattr(auto_match, "analyze_profile", lambda *a, **k: _analysis(80))

    calls = []
    _run(progress_callback=lambda done, total, title: calls.append((done, total, title)))

    assert calls == [(1, 2, "Job 1"), (2, 2, "Job 2")]


def test_progress_callback_optional(monkeypatch):
    monkeypatch.setattr(auto_match, "fetch_jobs", lambda *a, **k: ([_make_job(1)], 1))
    monkeypatch.setattr(auto_match, "fetch_job_description", lambda url: "Full JD")
    monkeypatch.setattr(auto_match, "analyze_profile", lambda *a, **k: _analysis(80))

    result = _run()
    assert result["total_matched"] == 1


# --------------------------------------------------------------------------
# UI alias compatibility (auto_match_ui.py naming)
# --------------------------------------------------------------------------

def test_ui_alias_parameter_names(monkeypatch):
    captured_jobs = {}
    captured_ai = {}

    def fake_fetch_jobs(query, location, country, results_per_page, app_id, app_key):
        captured_jobs.update(locals())
        return ([_make_job(1)], 1)

    def fake_analyze(profile_text, job_description, provider, model, prompt, language, **kw):
        captured_ai.update(
            {
                "profile": profile_text,
                "provider": provider,
                "model": model,
                "language": language,
                "api_key": kw.get("api_key"),
            }
        )
        return _analysis(88)

    monkeypatch.setattr(auto_match, "fetch_jobs", fake_fetch_jobs)
    monkeypatch.setattr(auto_match, "fetch_job_description", lambda url: "Full JD")
    monkeypatch.setattr(auto_match, "analyze_profile", fake_analyze)

    # Exactly the keyword names used by auto_match_ui.py
    result = run_auto_match(
        cv_text="UI profile text",
        keyword="data analyst",
        location="",
        country="us",
        results_per_page=10,
        threshold=60,
        app_id="ui-app-id",
        app_key="ui-app-key",
        provider="gemini",
        model="gemini-9.2-flash",
        api_key="ui-ai-key",
        language="Portuguese (Brazil)",
    )

    assert captured_jobs["query"] == "data analyst"
    assert captured_jobs["app_id"] == "ui-app-id"
    assert captured_jobs["app_key"] == "ui-app-key"
    assert captured_jobs["country"] == "us"
    assert captured_ai["profile"] == "UI profile text"
    assert captured_ai["provider"] == "gemini"
    assert captured_ai["model"] == "gemini-9.2-flash"
    assert captured_ai["api_key"] == "ui-ai-key"
    assert captured_ai["language"] == "Portuguese (Brazil)"
    assert result["results"][0]["status"] == "matched"