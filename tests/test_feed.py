from pathlib import Path

import pytest

from pipeline.errors import Blocked
from pipeline.sources.feed import Feed, FeedPost

POSTS = [
    FeedPost("NEW", "2026-09-30", True),
    FeedPost("IMG", "2026-09-29", False),
    FeedPost("OLD", "2026-09-01", True),
]


class FakeFetch:
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def __call__(self, username, cookies, limit):
        self.calls.append((username, cookies, limit))
        out = self.outcomes.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


def test_anonymous_success_returns_videos_oldest_first():
    fetch = FakeFetch(POSTS)
    posts = Feed("bourr_", None, fetch=fetch).latest_reels()
    assert [p.shortcode for p in posts] == ["OLD", "NEW"]
    assert fetch.calls == [("bourr_", None, 12)]


def test_anonymous_failure_retries_with_cookies():
    cookies = Path("/secret/cookies.txt")
    fetch = FakeFetch(RuntimeError("401 Unauthorized"), POSTS)
    Feed("bourr_", cookies, fetch=fetch).latest_reels()
    assert [c[1] for c in fetch.calls] == [None, cookies]


def test_anonymous_failure_without_cookies_is_blocked():
    with pytest.raises(Blocked, match="anonyme"):
        Feed("bourr_", None, fetch=FakeFetch(RuntimeError("login required"))).latest_reels()


def test_failure_with_cookies_too_is_blocked():
    fetch = FakeFetch(RuntimeError("401"), RuntimeError("checkpoint"))
    with pytest.raises(Blocked, match="cookies"):
        Feed("bourr_", Path("/c.txt"), fetch=fetch).latest_reels()
