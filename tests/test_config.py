from pathlib import Path

import pytest

from pipeline.config import load_config

EXAMPLE = Path(__file__).resolve().parents[1] / "config.example.toml"
WHISPER = '[whisper]\nbin = "~/w"\ngpu_model = "~/g.bin"\ncpu_model = "~/c.bin"\n'


def test_example_config_loads_with_documented_defaults():
    cfg = load_config(EXAMPLE)
    assert cfg.account == "bourr_"
    assert cfg.max_reels_per_run == 30
    assert cfg.max_attempts == 3
    assert (cfg.delay_min_s, cfg.delay_max_s) == (20, 60)
    assert cfg.cookies_file is None
    assert cfg.claude_model == "claude-sonnet-5-5"
    assert cfg.whisper.use_gpu is True
    assert not str(cfg.whisper.bin).startswith("~")


def test_missing_keys_use_defaults_and_tilde_is_expanded(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text('cookies_file = "~/ig.txt"\n' + WHISPER)
    cfg = load_config(p)
    assert cfg.cookies_file == Path.home() / "ig.txt"
    assert cfg.whisper.gpu_model == Path.home() / "g.bin"
    assert cfg.max_attempts == 3
    assert cfg.account == "bourr_"


def test_inverted_delays_are_rejected(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text("delay_min_s = 10\ndelay_max_s = 5\n" + WHISPER)
    with pytest.raises(ValueError, match="delay_min_s"):
        load_config(p)
