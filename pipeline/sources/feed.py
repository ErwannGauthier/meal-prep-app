import http.cookiejar
from collections.abc import Callable
from dataclasses import dataclass
from itertools import islice
from pathlib import Path

from ..errors import Blocked


@dataclass(frozen=True)
class FeedPost:
    shortcode: str
    posted_at: str
    is_video: bool


FetchFn = Callable[[str, Path | None, int], list[FeedPost]]


def instaloader_fetch(username: str, cookies: Path | None, limit: int) -> list[FeedPost]:
    import instaloader

    loader = instaloader.Instaloader(
        quiet=True, download_pictures=False, download_videos=False,
        download_video_thumbnails=False, download_comments=False,
        save_metadata=False, max_connection_attempts=1,
    )
    if cookies:
        jar = http.cookiejar.MozillaCookieJar(str(cookies))
        jar.load(ignore_discard=True, ignore_expires=True)
        loader.load_session("cookies", {c.name: c.value for c in jar if "instagram.com" in c.domain})
    profile = instaloader.Profile.from_username(loader.context, username)
    return [
        FeedPost(p.shortcode, p.date_utc.date().isoformat(), p.is_video)
        for p in islice(profile.get_posts(), limit)
    ]


class Feed:
    def __init__(self, username: str, cookies: Path | None, limit: int = 12,
                 fetch: FetchFn = instaloader_fetch):
        self.username = username
        self.cookies = cookies
        self.limit = limit
        self.fetch = fetch

    def latest_reels(self) -> list[FeedPost]:
        # Toute exception est traitée comme un refus : instaloader lève des types variés
        # (LoginRequired, TooManyRequests, Connection, KeyError sur un cookie absent…).
        try:
            posts = self.fetch(self.username, None, self.limit)
        except Exception as e:
            if not self.cookies:
                raise Blocked(f"feed anonyme refusé : {e}") from e
            try:
                posts = self.fetch(self.username, self.cookies, self.limit)
            except Exception as e2:
                raise Blocked(f"feed refusé même avec les cookies : {e2}") from e2
        return sorted((p for p in posts if p.is_video), key=lambda p: p.posted_at)
