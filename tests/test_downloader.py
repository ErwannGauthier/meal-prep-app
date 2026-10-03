import json
from pathlib import Path

import pytest

from pipeline.downloader import Downloader
from pipeline.errors import Blocked, ReelError
from pipeline.proc import CmdResult
from tests.conftest import FakeRunner, fail, ok

LOGIN = "ERROR: [Instagram] ABC: Requested content is not available, rate-limit reached or login required. Use --cookies"
GONE = "ERROR: [Instagram] ABC: This content is no longer available"


def success(work: Path, rid: str, thumb: bool = True):
    def write():
        (work / f"{rid}.wav").write_bytes(b"RIFF")
        (work / f"{rid}.info.json").write_text(
            json.dumps({"description": "Meal prep poulet", "upload_date": "20260514"})
        )
        if thumb:
            (work / f"{rid}.jpg").write_bytes(b"jpg")
    return write


def make_runner(ytdlp_outcomes: list) -> FakeRunner:
    queue = list(ytdlp_outcomes)

    def handler(args):
        if "yt_dlp" in args:
            item = queue.pop(0)
            if isinstance(item, CmdResult):
                return item
            item()
            return ok()
        if args[0] == "ffmpeg":
            Path(args[-1]).write_bytes(b"out")
            return ok()
        raise AssertionError(f"commande inattendue : {args}")

    return FakeRunner(handler)


def ytdlp_calls(runner):
    return [c.args for c in runner.calls if "yt_dlp" in c.args]


@pytest.fixture
def dirs(tmp_path):
    return tmp_path / "work", tmp_path / "thumbs"


def test_fetch_returns_16k_wav_caption_date_and_webp(dirs):
    work, thumbs = dirs
    runner = make_runner([success(work, "ABC")])
    d = Downloader(work, thumbs, cookies=None, runner=runner).fetch("ABC")
    assert d.wav == work / "ABC.16k.wav" and d.wav.exists()
    assert not (work / "ABC.wav").exists()
    assert d.caption == "Meal prep poulet"
    assert d.posted_at == "2026-05-14"
    assert d.thumbnail == thumbs / "ABC.webp" and d.thumbnail.exists()
    [args] = ytdlp_calls(runner)
    assert "--cookies" not in args
    assert args[-1] == "https://www.instagram.com/reel/ABC/"


def test_missing_thumbnail_is_not_an_error(dirs):
    work, thumbs = dirs
    d = Downloader(work, thumbs, None, make_runner([success(work, "ABC", thumb=False)])).fetch("ABC")
    assert d.thumbnail is None


def test_blocked_without_cookies_raises_blocked(dirs):
    work, thumbs = dirs
    with pytest.raises(Blocked):
        Downloader(work, thumbs, None, make_runner([fail(LOGIN)])).fetch("ABC")


def test_blocked_retries_with_cookies_then_sticks_to_cookies(dirs, tmp_path):
    work, thumbs = dirs
    cookies = tmp_path / "cookies.txt"
    runner = make_runner([fail(LOGIN), success(work, "ABC"), success(work, "DEF")])
    dl = Downloader(work, thumbs, cookies, runner)
    dl.fetch("ABC")
    dl.fetch("DEF")
    calls = ytdlp_calls(runner)
    assert len(calls) == 3
    assert "--cookies" not in calls[0]
    assert "--cookies" in calls[1] and "--cookies" in calls[2]


def test_blocked_even_with_cookies_raises_blocked(dirs, tmp_path):
    work, thumbs = dirs
    with pytest.raises(Blocked):
        Downloader(work, thumbs, tmp_path / "c.txt", make_runner([fail(LOGIN), fail(LOGIN)])).fetch("ABC")


def test_deleted_reel_is_a_reel_error_not_a_block(dirs, tmp_path):
    work, thumbs = dirs
    runner = make_runner([fail(GONE)])
    with pytest.raises(ReelError, match="no longer available"):
        Downloader(work, thumbs, tmp_path / "c.txt", runner).fetch("ABC")
    assert len(ytdlp_calls(runner)) == 1


def test_audio_conversion_failure_is_a_reel_error(dirs):
    work, thumbs = dirs

    def handler(args):
        if "yt_dlp" in args:
            success(work, "ABC")()
            return ok()
        return fail("ffmpeg: invalid data")

    with pytest.raises(ReelError, match="ffmpeg"):
        Downloader(work, thumbs, None, FakeRunner(handler)).fetch("ABC")


def test_cleanup_removes_only_this_reel_work_files(dirs):
    work, thumbs = dirs
    work.mkdir(parents=True)
    for name in ["ABC.16k.wav", "ABC.info.json", "ABCD.wav"]:
        (work / name).write_bytes(b"x")
    Downloader(work, thumbs, None, make_runner([])).cleanup("ABC")
    assert sorted(p.name for p in work.iterdir()) == ["ABCD.wav"]


def test_probe_checks_a_reel_without_downloading_anything(dirs):
    work, thumbs = dirs
    runner = FakeRunner(lambda args: ok())
    assert Downloader(work, thumbs, None, runner).probe("REF") is True
    [args] = ytdlp_calls(runner)
    assert "--simulate" in args and args[-1] == "https://www.instagram.com/reel/REF/"
    assert not work.exists() or list(work.iterdir()) == []


def test_probe_is_false_when_instagram_refuses(dirs):
    work, thumbs = dirs
    assert Downloader(work, thumbs, None, FakeRunner(lambda args: fail(LOGIN))).probe("REF") is False
