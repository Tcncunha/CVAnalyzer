import pytest

import profile_manager


@pytest.fixture(autouse=True)
def _isolated_profiles(tmp_path, monkeypatch):
    monkeypatch.setattr(profile_manager, "PROFILES_DIR", tmp_path)
    yield


def test_save_and_load_profile():
    file_path = profile_manager.save_profile("Thiago Cunha", {"name": "Thiago"})
    assert file_path.exists()
    assert profile_manager.load_profile("Thiago Cunha") == {"name": "Thiago"}


def test_save_profile_with_persist_false_writes_nothing():
    result = profile_manager.save_profile("Ana", {"name": "Ana"}, persist=False)
    assert result == {"name": "Ana"}
    assert profile_manager.list_saved_profiles() == []


def test_save_sanitizes_illegal_filename_chars():
    file_path = profile_manager.save_profile("a/b:c*d", {"x": 1})
    assert "a_b_c_d.json" in file_path.name


def test_load_missing_profile_returns_none():
    assert profile_manager.load_profile("ghost") is None


def test_clear_all_profiles():
    profile_manager.save_profile("P1", {"x": 1})
    profile_manager.save_profile("P2", {"x": 2})
    assert profile_manager.clear_all_profiles() == 2
    assert profile_manager.list_saved_profiles() == []