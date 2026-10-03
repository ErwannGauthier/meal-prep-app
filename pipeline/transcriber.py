import logging
from pathlib import Path

from .config import WhisperConfig
from .errors import ReelError
from .proc import Runner, run_cmd

log = logging.getLogger(__name__)


class Transcriber:
    def __init__(self, cfg: WhisperConfig, runner: Runner = run_cmd, force_cpu: bool = False):
        self.cfg = cfg
        self.runner = runner
        self.use_gpu = cfg.use_gpu and not force_cpu

    def transcribe(self, wav: Path) -> str:
        if self.use_gpu:
            try:
                return self._run(wav, gpu=True)
            except ReelError as e:
                log.warning("Whisper GPU en échec (%s), nouvel essai sur CPU", e)
        return self._run(wav, gpu=False)

    def _run(self, wav: Path, gpu: bool) -> str:
        model = self.cfg.gpu_model if gpu else self.cfg.cpu_model
        base = str(wav.with_suffix(""))
        args = [str(self.cfg.bin), "-m", str(model), "-f", str(wav),
                "-l", "fr", "-nt", "-otxt", "-of", base]
        if not gpu:
            args.append("-ng")
        res = self.runner(args, timeout=1800)
        txt = Path(base + ".txt")
        if res.returncode != 0 or not txt.exists():
            detail = (res.stderr.strip().splitlines() or ["pas de sortie"])[-1][:300]
            raise ReelError(f"whisper ({'GPU' if gpu else 'CPU'}) : {detail}")
        text = txt.read_text(encoding="utf-8", errors="replace")
        txt.unlink()
        return "\n".join(line.strip() for line in text.splitlines() if line.strip())
