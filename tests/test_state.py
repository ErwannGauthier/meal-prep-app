import re

from pipeline.models import State
from pipeline.state import add_pending, give_up, now_iso, record_attempt, retry_failed, select_batch, stall


def test_now_iso_is_utc_seconds_with_z():
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", now_iso())


def test_add_pending_skips_known_and_keeps_order():
    s = State()
    assert add_pending(s, ["A", "B"], "notion") == ["A", "B"]
    assert add_pending(s, ["B", "C", "C"], "feed") == ["C"]
    assert list(s.reels) == ["A", "B", "C"]
    assert s.reels["B"].source == "notion"
    assert s.reels["C"].source == "feed"
    assert s.reels["C"].status == "pending"


def test_select_batch_takes_pending_and_retryable_failed_in_order():
    s = State()
    add_pending(s, ["A", "B", "C", "D", "E"], "notion")
    record_attempt(s, "A", "done")
    record_attempt(s, "B", "failed", "boom")          # 1 tentative < 3 → repris
    record_attempt(s, "C", "not_meal_prep")
    for _ in range(3):
        record_attempt(s, "D", "failed", "boom")      # 3 tentatives → abandonné
    assert select_batch(s, limit=10, max_attempts=3) == ["B", "E"]
    assert select_batch(s, limit=1, max_attempts=3) == ["B"]


def test_record_attempt_updates_status_error_and_counter():
    s = State()
    add_pending(s, ["A"], "feed")
    record_attempt(s, "A", "failed", "réseau")
    record_attempt(s, "A", "done")
    r = s.reels["A"]
    assert (r.status, r.error, r.attempts) == ("done", None, 2)


def test_give_up_marks_failed_and_excludes_from_batches():
    s = State()
    add_pending(s, ["A"], "notion")
    give_up(s, "A", "classé non meal prep", max_attempts=3)
    assert (s.reels["A"].status, s.reels["A"].error) == ("failed", "classé non meal prep")
    assert select_batch(s, limit=10, max_attempts=3) == []


def test_stall_counts_interrupted_runs_and_gives_up_at_the_limit():
    s = State()
    add_pending(s, ["A"], "notion")
    assert stall(s, "A", "use --cookies", limit=2, max_attempts=3) is False
    assert (s.reels["A"].status, s.reels["A"].stalls, s.reels["A"].attempts) == ("pending", 1, 0)
    assert stall(s, "A", "use --cookies", limit=2, max_attempts=3) is True
    assert s.reels["A"].status == "failed"
    assert "2 lancements" in s.reels["A"].error
    assert select_batch(s, limit=10, max_attempts=3) == []


def test_a_recorded_attempt_resets_the_stall_counter():
    s = State()
    add_pending(s, ["A"], "notion")
    stall(s, "A", "x", limit=5, max_attempts=3)
    record_attempt(s, "A", "done")
    assert s.reels["A"].stalls == 0


def test_retry_failed_requeues_all_or_selected_failed_reels():
    s = State()
    add_pending(s, ["A", "B", "C"], "notion")
    give_up(s, "A", "boom", max_attempts=3)
    give_up(s, "B", "boom", max_attempts=3)
    record_attempt(s, "C", "done")
    assert retry_failed(s, ["B", "C", "INCONNU"]) == ["B"]
    assert (s.reels["B"].status, s.reels["B"].attempts, s.reels["B"].error) == ("pending", 0, None)
    assert s.reels["C"].status == "done"
    assert retry_failed(s, None) == ["A"]
