import pytest

from providers import detect_provider_from_key


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