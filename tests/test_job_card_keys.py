"""Unit tests for the job-card widget key generator (H1 regression)."""

from ui import _job_card_key


def _job(source, job_id):
    return {"id": job_id, "source": source}


def test_same_id_across_sources_do_not_collide():
    assert _job_card_key("use_job", _job("adzuna", "123"), 0) != _job_card_key(
        "use_job", _job("jooble", "123"), 0
    )


def test_use_and_open_prefixes_are_distinct():
    job = _job("adzuna", "7")
    assert _job_card_key("use_job", job, 0) != _job_card_key("open_job", job, 0)


def test_missing_id_falls_back_to_card_index():
    assert _job_card_key("use_job", _job("adzuna", None), 3) == "use_job_idx_3"
    assert _job_card_key("use_job", _job("adzuna", ""), 3) == "use_job_idx_3"


def test_missing_source_and_id_unique_per_index():
    assert _job_card_key("use_job", _job(None, None), 0) != _job_card_key(
        "use_job", _job(None, None), 1
    )


def test_key_is_stable_for_the_same_card():
    assert _job_card_key("open_job", _job("jooble", "99"), 2) == "open_job_jooble_99"