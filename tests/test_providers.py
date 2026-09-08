import pytest

from providers import (
    _OPENCODE_SESSION_ID,
    _opencode_headers,
    detect_provider_from_key,
    is_free_zen_model,
)


@pytest.mark.parametrize(
    "key,provider",
    [
        ("AIzaSyA-fake-gemini-key", "gemini"),
        ("sk-ant-api03-fake", "anthropic"),
        ("sk-proj-fake-openai", "openai"),
        ("sk-svcacct-fake", "openai"),
        ("ghp_fake-github-token", "copilot"),
        ("github_pat_123_fake", "copilot"),
        ("sk-fake-openai-legacy" + "T3BlbkFJ", "openai"),
        ("sk-fake-opencode-zen", "opencode_zen"),
        ("", None),
        ("unknown-prefix-xyz", None),
    ],
)
def test_detect_provider_from_key(key, provider):
    assert detect_provider_from_key(key) == provider


def test_unknown_provider_detection_none():
    assert detect_provider_from_key("not a key at all") is None


# ---------------------------------------------------------------------------
# OpenCode Zen session-header fix (MissingSessionID workaround)
# ---------------------------------------------------------------------------

def test_opencode_headers_for_zen():
    headers = _opencode_headers("opencode_zen")
    assert headers is not None
    assert headers["x-opencode-session"] == _OPENCODE_SESSION_ID
    assert "User-Agent" in headers
    assert headers["User-Agent"].startswith("CV-Analyzer/")


@pytest.mark.parametrize("provider", ["gemini", "openai", "anthropic", "copilot"])
def test_opencode_headers_none_for_other_providers(provider):
    assert _opencode_headers(provider) is None


def test_opencode_session_id_stable():
    assert _opencode_headers("opencode_zen")["x-opencode-session"] == _OPENCODE_SESSION_ID


@pytest.mark.parametrize(
    "model,expected",
    [
        ("big-pickle", True),
        ("deepseek-v4-flash-free", True),
        ("mimo-v2.5-free", True),
        ("nemotron-3.5-lightning-free", True),
        ("ling-3.0-flash-fin-free", True),
        ("muse-spark-1.3-contributor-free", True),
        ("deepseek-v4-flash", False),
        ("glm-5.3-flash", False),
        ("gpt-5.6-luna", False),
        ("", False),
    ],
)
def test_is_free_zen_model(model, expected):
    assert is_free_zen_model(model) is expected