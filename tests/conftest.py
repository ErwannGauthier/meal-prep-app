from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from pipeline.proc import CmdResult


def ok(stdout: str = "") -> CmdResult:
    return CmdResult(0, stdout, "")


def fail(stderr: str, code: int = 1) -> CmdResult:
    return CmdResult(code, "", stderr)


@dataclass
class Call:
    args: list[str]
    input: str | None
    cwd: Path | None


class FakeRunner:
    """Remplace run_cmd : enregistre les appels et délègue la réponse à `handler(args)`."""

    def __init__(self, handler: Callable[[list[str]], CmdResult]):
        self.handler = handler
        self.calls: list[Call] = []

    def __call__(self, args, *, input=None, cwd=None, timeout=900) -> CmdResult:
        self.calls.append(Call(list(args), input, cwd))
        return self.handler(list(args))
