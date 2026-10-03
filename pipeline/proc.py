import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class CmdResult:
    returncode: int
    stdout: str
    stderr: str


class Runner(Protocol):
    def __call__(
        self,
        args: list[str],
        *,
        input: str | None = None,
        cwd: Path | None = None,
        timeout: float = 900,
    ) -> CmdResult: ...


def run_cmd(
    args: list[str],
    *,
    input: str | None = None,
    cwd: Path | None = None,
    timeout: float = 900,
) -> CmdResult:
    stdin = {"input": input} if input is not None else {"stdin": subprocess.DEVNULL}
    try:
        p = subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, errors="replace", timeout=timeout, **stdin
        )
    except FileNotFoundError:
        return CmdResult(127, "", f"commande introuvable : {args[0]}")
    except subprocess.TimeoutExpired:
        return CmdResult(124, "", f"délai dépassé ({timeout:.0f} s) : {args[0]}")
    return CmdResult(p.returncode, p.stdout, p.stderr)
