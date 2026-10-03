from pathlib import Path

import pytest

from pipeline.config import WhisperConfig
from pipeline.errors import ReelError
from pipeline.transcriber import Transcriber
from tests.conftest import FakeRunner, fail, ok

CFG = WhisperConfig(bin=Path("/opt/whisper-cli"), gpu_model=Path("/m/large.bin"),
                    cpu_model=Path("/m/small.bin"), use_gpu=True)


def whisper(text: str = " Bonjour \n\n  on prépare du poulet \n", gpu_ok: bool = True):
    def handler(args):
        if "-ng" not in args and not gpu_ok:
            return fail("ggml_vulkan: no device found")
        out = Path(args[args.index("-of") + 1] + ".txt")
        out.write_text(text, encoding="utf-8")
        return ok()
    return FakeRunner(handler)


@pytest.fixture
def wav(tmp_path):
    p = tmp_path / "ABC.16k.wav"
    p.write_bytes(b"RIFF")
    return p


def test_gpu_transcription_returns_clean_lines_and_removes_txt(wav):
    runner = whisper()
    text = Transcriber(CFG, runner).transcribe(wav)
    assert text == "Bonjour\non prépare du poulet"
    [call] = runner.calls
    assert call.args[:3] == ["/opt/whisper-cli", "-m", "/m/large.bin"]
    assert ["-l", "fr"] == call.args[call.args.index("-l"):call.args.index("-l") + 2]
    assert "-ng" not in call.args
    assert list(wav.parent.glob("*.txt")) == []


def test_gpu_failure_falls_back_to_cpu(wav):
    runner = whisper(gpu_ok=False)
    assert Transcriber(CFG, runner).transcribe(wav).startswith("Bonjour")
    assert len(runner.calls) == 2
    assert "-ng" in runner.calls[1].args and "/m/small.bin" in runner.calls[1].args


@pytest.mark.parametrize("cfg,force_cpu", [
    (WhisperConfig(CFG.bin, CFG.gpu_model, CFG.cpu_model, use_gpu=False), False),
    (CFG, True),
])
def test_cpu_only_modes_never_try_gpu(wav, cfg, force_cpu):
    runner = whisper()
    Transcriber(cfg, runner, force_cpu=force_cpu).transcribe(wav)
    [call] = runner.calls
    assert "-ng" in call.args


def test_cpu_failure_is_a_reel_error(wav):
    runner = FakeRunner(lambda args: fail("whisper: failed to read audio"))
    with pytest.raises(ReelError, match="whisper"):
        Transcriber(CFG, runner).transcribe(wav)


def test_music_only_reel_gives_empty_transcript(wav):
    assert Transcriber(CFG, whisper(text="\n\n")).transcribe(wav) == ""


def test_invalid_utf8_in_whisper_output_is_not_fatal(wav):
    def handler(args):
        Path(args[args.index("-of") + 1] + ".txt").write_bytes(b"du poulet \xff grill\xc3\xa9\n")
        return ok()
    assert Transcriber(CFG, FakeRunner(handler)).transcribe(wav).startswith("du poulet")
