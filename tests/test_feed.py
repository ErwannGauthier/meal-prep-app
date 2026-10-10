from pathlib import Path

import pytest

from pipeline.errors import Blocked
from pipeline.sources.feed import Feed, FeedPost, gallery_dl_fetch


def reel(code: str) -> FeedPost:
    return FeedPost(code)


def pinned(code: str) -> FeedPost:
    return FeedPost(code, pinned=True)


class FakeFetch:
    """Onglet Reels simulé : renvoie les reels un à un, épinglés d'abord, puis du plus récent au plus ancien."""

    def __init__(self, posts=(), error: Exception | None = None, fail_after: int | None = None):
        self.posts, self.error, self.fail_after = list(posts), error, fail_after
        self.calls: list[tuple[str, Path | None]] = []
        self.read = 0   # nombre de reels réellement lus sur Instagram

    def __call__(self, username, cookies):
        self.calls.append((username, cookies))
        if self.error:
            raise self.error
        return self._iterate()

    def _iterate(self):
        for post in self.posts:
            if self.fail_after is not None and self.read >= self.fail_after:
                raise RuntimeError("429 Too Many Requests")
            self.read += 1
            yield post


def test_walks_back_until_a_known_reel_and_returns_new_ones_oldest_first():
    fetch = FakeFetch([reel("N3"), reel("N2"), reel("N1"), reel("KNOWN"), reel("OLDER")])
    posts = Feed("bourr_", None, fetch=fetch).latest_reels({"KNOWN"})
    assert [p.shortcode for p in posts] == ["N1", "N2", "N3"]
    assert fetch.read == 4                     # s'arrête sur KNOWN, OLDER n'est jamais lu


def test_known_pinned_reels_do_not_stop_the_walk():
    fetch = FakeFetch([pinned("PIN1"), pinned("PIN2"), reel("N1"), reel("KNOWN"), reel("OLDER")])
    posts = Feed("bourr_", None, fetch=fetch).latest_reels({"PIN1", "PIN2", "KNOWN"})
    assert [p.shortcode for p in posts] == ["N1"]
    assert fetch.read == 4


def test_unknown_pinned_reels_are_collected_and_come_first():
    # Un reel épinglé est ancien : il passe avant les nouveautés dans la file.
    fetch = FakeFetch([pinned("PIN_NEW"), reel("N2"), reel("N1"), reel("KNOWN")])
    posts = Feed("bourr_", None, fetch=fetch).latest_reels({"KNOWN"})
    assert [p.shortcode for p in posts] == ["PIN_NEW", "N1", "N2"]


def test_nothing_new_reads_only_up_to_the_first_known_reel():
    fetch = FakeFetch([pinned("PIN")] + [reel(f"K{i}") for i in range(20)])
    posts = Feed("bourr_", None, fetch=fetch).latest_reels({"PIN"} | {f"K{i}" for i in range(20)})
    assert posts == [] and fetch.read == 2


def test_stops_at_the_safety_cap_when_no_known_reel_is_met():
    fetch = FakeFetch([reel(f"N{i}") for i in range(80)])
    posts = Feed("bourr_", None, max_posts=50, fetch=fetch).latest_reels(set())
    assert len(posts) == 50 and fetch.read == 50
    assert posts[0].shortcode == "N49" and posts[-1].shortcode == "N0"


def test_with_cookies_the_profile_is_read_logged_in_straight_away():
    cookies = Path("/secret/cookies.txt")
    fetch = FakeFetch([reel("N1")])
    Feed("bourr_", cookies, fetch=fetch).latest_reels(set())
    assert fetch.calls == [("bourr_", cookies)]       # aucun essai sans compte


def test_without_cookies_a_refusal_says_an_account_is_needed():
    fetch = FakeFetch(error=RuntimeError("401 require_login"))
    with pytest.raises(Blocked, match="sans compte"):
        Feed("bourr_", None, fetch=fetch).latest_reels(set())
    assert fetch.calls == [("bourr_", None)]


def test_refusal_with_cookies_is_reported_as_such():
    fetch = FakeFetch(error=RuntimeError("checkpoint_required"))
    with pytest.raises(Blocked, match="avec les cookies.*checkpoint_required"):
        Feed("bourr_", Path("/c.txt"), fetch=fetch).latest_reels(set())
    assert len(fetch.calls) == 1


def test_refusal_while_reading_a_later_page_is_blocked_too():
    fetch = FakeFetch([reel(f"N{i}") for i in range(30)], fail_after=12)
    with pytest.raises(Blocked, match="429"):
        Feed("bourr_", Path("/c.txt"), fetch=fetch).latest_reels(set())


# --- adaptateur gallery-dl ---------------------------------------------------

class FakeGalleryDl:
    """Remplace gallery_dl.extractor.find : un extracteur dont l'API liste des reels."""

    def __init__(self, nodes):
        self.nodes, self.url, self.initialized, self.asked = nodes, None, False, None
        self.api = self

    def find(self, url):
        self.url = url
        return self

    def initialize(self):
        self.initialized = True

    def user_reels(self, username):
        self.asked = username
        yield from self.nodes


def node(code, pinned_ids=()):
    return {"__typename": "XDTClipsItem", "media": {"code": code, "clips_tab_pinned_user_ids": list(pinned_ids)}}


def test_gallery_dl_adapter_maps_reels_and_pinned_flag(monkeypatch, tmp_path):
    from gallery_dl import config, extractor
    fake = FakeGalleryDl([node("PIN", ["186869497"]), node("N1"), {"media": {"code": "N0"}}])
    monkeypatch.setattr(extractor, "find", fake.find)
    cookies = tmp_path / "cookies.txt"
    posts = list(gallery_dl_fetch("bourr_", cookies))
    assert posts == [FeedPost("PIN", pinned=True), FeedPost("N1"), FeedPost("N0")]
    assert fake.url == "https://www.instagram.com/bourr_/reels/" and fake.initialized and fake.asked == "bourr_"
    section = ("extractor", "instagram")
    assert config.get(section, "cookies") == str(cookies)
    assert config.get(section, "cookies-update") is False     # le fichier de l'utilisateur n'est jamais réécrit


def test_gallery_dl_adapter_without_cookies_does_not_reuse_a_previous_session(monkeypatch, tmp_path):
    from gallery_dl import config, extractor
    monkeypatch.setattr(extractor, "find", FakeGalleryDl([]).find)
    list(gallery_dl_fetch("bourr_", tmp_path / "cookies.txt"))
    list(gallery_dl_fetch("bourr_", None))
    assert config.get(("extractor", "instagram"), "cookies") is None


def test_gallery_dl_adapter_fails_clearly_when_the_url_is_not_recognised(monkeypatch):
    from gallery_dl import extractor
    monkeypatch.setattr(extractor, "find", lambda url: None)
    with pytest.raises(RuntimeError, match="gallery-dl"):
        list(gallery_dl_fetch("bourr_", None))
