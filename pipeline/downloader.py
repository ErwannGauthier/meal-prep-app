import json
import sys
from dataclasses import dataclass
from pathlib import Path

from .errors import Blocked, ReelError
from .proc import Runner, run_cmd

REEL_URL = "https://www.instagram.com/reel/{}/"

# Messages (en minuscules) qui signifient « Instagram refuse », par opposition
# à « ce reel n'existe plus ». Compléter avec les résultats du spike.
BLOCK_MARKERS = (
    "login required",
    "rate-limit",
    "rate limit",
    "too many requests",
    "http error 429",
    "please wait a few minutes",
    "checkpoint_required",
    "--cookies",
)


def _is_blocked(stderr: str) -> bool:
    s = stderr.lower()
    return any(m in s for m in BLOCK_MARKERS)


def _last_line(text: str) -> str:
    lines = [l for l in text.strip().splitlines() if l.strip()]
    return lines[-1][:300] if lines else "erreur inconnue"


def _iso_date(upload_date: str | None) -> str | None:
    if not upload_date or len(upload_date) != 8:
        return None
    return f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"


@dataclass(frozen=True)
class Download:
    wav: Path
    caption: str
    posted_at: str | None
    thumbnail: Path | None


class Downloader:
    def __init__(self, work_dir: Path, thumbs_dir: Path, cookies: Path | None, runner: Runner = run_cmd):
        self.work_dir = work_dir
        self.thumbs_dir = thumbs_dir
        self.cookies = cookies
        self.runner = runner
        self._use_cookies = False  # passe à True dès qu'Instagram a refusé l'accès anonyme

    def fetch(self, reel_id: str) -> Download:
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.thumbs_dir.mkdir(parents=True, exist_ok=True)

        res = self._yt_dlp(reel_id, with_cookies=self._use_cookies)
        if res.returncode != 0 and _is_blocked(res.stderr) and self.cookies and not self._use_cookies:
            self._use_cookies = True
            res = self._yt_dlp(reel_id, with_cookies=True)
        if res.returncode != 0:
            if _is_blocked(res.stderr):
                raise Blocked(_last_line(res.stderr))
            raise ReelError(f"yt-dlp : {_last_line(res.stderr)}")

        raw_wav = self.work_dir / f"{reel_id}.wav"
        if not raw_wav.exists():
            raise ReelError("yt-dlp n'a pas produit de fichier audio")
        wav = self.work_dir / f"{reel_id}.16k.wav"
        conv = self.runner(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw_wav), "-ac", "1", "-ar", "16000", str(wav)]
        )
        raw_wav.unlink(missing_ok=True)
        if conv.returncode != 0:
            raise ReelError(f"ffmpeg (audio) : {_last_line(conv.stderr)}")

        info_path = self.work_dir / f"{reel_id}.info.json"
        info = json.loads(info_path.read_text(encoding="utf-8")) if info_path.exists() else {}
        return Download(
            wav=wav,
            caption=info.get("description") or "",
            posted_at=_iso_date(info.get("upload_date")),
            thumbnail=self._thumbnail(reel_id),
        )

    def probe(self, reel_id: str) -> bool:
        """Instagram répond-il pour ce reel ? Ne télécharge rien."""
        args = [sys.executable, "-m", "yt_dlp", "--no-progress", "--no-playlist", "--simulate"]
        if self._use_cookies and self.cookies:
            args += ["--cookies", str(self.cookies)]
        args.append(REEL_URL.format(reel_id))
        return self.runner(args, timeout=120).returncode == 0

    def cleanup(self, reel_id: str) -> None:
        if not self.work_dir.exists():
            return
        for p in self.work_dir.glob(f"{reel_id}.*"):
            p.unlink(missing_ok=True)

    def _yt_dlp(self, reel_id: str, with_cookies: bool):
        args = [
            sys.executable, "-m", "yt_dlp",
            "--no-progress", "--no-playlist",
            "-f", "ba/b", "-x", "--audio-format", "wav",
            "--write-info-json", "--write-thumbnail", "--convert-thumbnails", "jpg",
            "-o", str(self.work_dir / f"{reel_id}.%(ext)s"),
        ]
        if with_cookies and self.cookies:
            args += ["--cookies", str(self.cookies)]
        args.append(REEL_URL.format(reel_id))
        return self.runner(args, timeout=600)

    def _thumbnail(self, reel_id: str) -> Path | None:
        jpg = self.work_dir / f"{reel_id}.jpg"
        if not jpg.exists():
            return None
        out = self.thumbs_dir / f"{reel_id}.webp"
        res = self.runner([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(jpg),
            "-vf", "scale='min(480,iw)':-2", "-c:v", "libwebp", "-quality", "80", str(out),
        ])
        jpg.unlink(missing_ok=True)
        return out if res.returncode == 0 and out.exists() else None
