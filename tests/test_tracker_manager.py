import pytest

import tracker_manager


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(tracker_manager, "DB_PATH", tmp_path / "tracker.db")
    tracker_manager.init_db()
    yield
    tracker_manager.clear_all()


def test_add_and_list_application():
    app_id = tracker_manager.add_application("Acme", "Backend Dev", cv_version="v2", job_url="https://x", notes="n")
    assert app_id > 0
    rows = tracker_manager.list_applications()
    assert len(rows) == 1
    assert rows[0]["company"] == "Acme"
    assert rows[0]["role"] == "Backend Dev"
    assert rows[0]["cv_version"] == "v2"
    assert rows[0]["job_url"] == "https://x"
    assert rows[0]["status"] == "applied"


def test_update_application():
    app_id = tracker_manager.add_application("Acme", "Dev")
    tracker_manager.update_application(app_id, status="interview", notes="agendada")
    rows = tracker_manager.list_applications()
    assert rows[0]["status"] == "interview"
    assert rows[0]["notes"] == "agendada"


def test_delete_application():
    app_id = tracker_manager.add_application("Acme", "Dev")
    tracker_manager.delete_application(app_id)
    assert tracker_manager.list_applications() == []


def test_get_stats_with_and_without_filter():
    tracker_manager.add_application("A", "Dev", cv_version="v1")
    tracker_manager.add_application("B", "Dev", cv_version="v1")
    tracker_manager.add_application("C", "Dev", cv_version="v2")
    app_id = tracker_manager.list_applications()[0]["id"]
    tracker_manager.update_application(app_id, status="offer")

    stats_all = tracker_manager.get_stats()
    assert stats_all["total"] == 3
    assert stats_all["by_status"]["offer"] == 1
    assert stats_all["conversion_offer"] == pytest.approx(33.3, abs=0.1)

    stats_v1 = tracker_manager.get_stats(cv_version="v1")
    assert stats_v1["total"] == 2


def test_default_follow_up_is_computed():
    app_id = tracker_manager.add_application("Acme", "Dev")
    rows = tracker_manager.list_applications()
    assert rows[0]["follow_up_date"]


def test_clear_all_removes_everything():
    tracker_manager.add_application("Acme", "Dev")
    tracker_manager.clear_all()
    assert tracker_manager.list_applications() == []
    assert tracker_manager.get_stats()["total"] == 0