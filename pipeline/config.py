import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WhisperConfig:
    bin: Path
    gpu_model: Path
    cpu_model: Path
    use_gpu: bool


@dataclass(frozen=True)
class Config:
    account: str
    max_reels_per_run: int
    max_attempts: int
    delay_min_s: float
    delay_max_s: float
    cookies_file: Path | None
    claude_model: str
    whisper: WhisperConfig


def _path(value: str) -> Path:
    return Path(value).expanduser()


def load_config(path: Path) -> Config:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    w = data["whisper"]
    cookies = data.get("cookies_file") or ""
    cfg = Config(
        account=data.get("account", "bourr_"),
        max_reels_per_run=int(data.get("max_reels_per_run", 30)),
        max_attempts=int(data.get("max_attempts", 3)),
        delay_min_s=float(data.get("delay_min_s", 20)),
        delay_max_s=float(data.get("delay_max_s", 60)),
        cookies_file=_path(cookies) if cookies else None,
        claude_model=data.get("claude_model", "claude-sonnet-5-5"),
        whisper=WhisperConfig(
            bin=_path(w["bin"]),
            gpu_model=_path(w["gpu_model"]),
            cpu_model=_path(w["cpu_model"]),
            use_gpu=bool(w.get("use_gpu", True)),
        ),
    )
    if cfg.delay_min_s > cfg.delay_max_s:
        raise ValueError("delay_min_s doit être inférieur ou égal à delay_max_s")
    return cfg
