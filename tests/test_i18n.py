import pytest

from i18n import DEFAULT_LANG, STRINGS

LANGS = ["pt", "en", "es"]

REQUIRED_KEYS = {
    "star_jd_empty",
    "star_answer_empty",
    "tracker_company_required",
    "tracker_role_required",
    "footer_credit",
    "footer_disclaimer",
    "app_title",
    "tracker_tab",
    "star_tab",
}


def test_all_locales_have_identical_key_sets():
    base = set(STRINGS["en"])
    for lang in LANGS:
        assert set(STRINGS[lang]) == base, f"mismatch in locale {lang}"


def test_required_keys_present():
    for lang in LANGS:
        missing = REQUIRED_KEYS - set(STRINGS[lang])
        assert not missing, f"locale {lang} missing keys: {missing}"


def test_default_lang_is_registered():
    assert DEFAULT_LANG in LANGS


def test_no_placeholder_or_dead_keys_remain():
    for lang in LANGS:
        assert "tracker_pick_cv" not in STRINGS[lang]


@pytest.mark.parametrize("lang", LANGS)
def test_no_empty_values(lang):
    empty = [k for k, v in STRINGS[lang].items() if not str(v).strip()]
    assert not empty, f"locale {lang} has empty values: {empty}"