import re
import zipfile
from pathlib import Path

SHORTCODE_RE = re.compile(
    r"instagram\.com/(?:[A-Za-z0-9_.]+/)?(?:reels?|p|tv)/([A-Za-z0-9_-]{5,})"
)
TEXT_SUFFIXES = {".csv", ".md", ".txt"}


def extract_shortcodes(text: str) -> list[str]:
    return list(dict.fromkeys(SHORTCODE_RE.findall(text)))


def _texts(path: Path) -> list[str]:
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as zf:
            names = sorted(n for n in zf.namelist() if Path(n).suffix in TEXT_SUFFIXES)
            return [zf.read(n).decode("utf-8", errors="replace") for n in names]
    if path.is_dir():
        files = sorted(p for p in path.rglob("*") if p.is_file() and p.suffix in TEXT_SUFFIXES)
        return [p.read_text(encoding="utf-8", errors="replace") for p in files]
    return [path.read_text(encoding="utf-8", errors="replace")]


def read_export(path: Path) -> list[str]:
    return extract_shortcodes("\n".join(_texts(path)))
