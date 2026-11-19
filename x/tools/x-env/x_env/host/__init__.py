"""Host adapters: run the same x-env command on another machine.

The core never runs ssh. `cli` forwards the whole command, minus `--host`,
before it loads any config, so the remote x-env does all the work with its
own config, its own git, and its own terminal. Paths in the command are
resolved on the host, from the remote user's home folder.

The forwarding protocol, one function per side:

  - local:  `forward(host, argv)` runs `x-env --forwarded <argv>` on the
    host, splits the mixed output, and returns the remote exit status.
  - remote: `--forwarded` makes `cli.main` run from the home folder inside
    `marked_stdout()`, which starts each stdout line with `STDOUT_MARKER`.

A transport may deliver stdout and stderr mixed (Rex captures one terminal),
so the marker is what tells them apart. Every unmarked line goes to local
stderr: git progress, a shell's "not found", or a traceback can never reach
a caller's `$(...)`.
"""

from __future__ import annotations

import contextlib
import io
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Protocol, TextIO

from ..model import XEnvError

STDOUT_MARKER = "x-env stdout: "
"""Starts each stdout line of a forwarded command. It never starts a line
that x-env writes to stderr (`x-env: `)."""

_COMMAND_NOT_FOUND = 127  # the shell's status when it cannot find the program


@dataclass(frozen=True)
class Completed:
    exit_code: int
    output: str  # stdout and stderr as the transport delivered them, possibly mixed


class Transport(Protocol):
    def run(self, label: str, argv: Sequence[str]) -> Completed:
        """Run `argv` on the host in its user's login environment, wait for
        it, and return its exit status and output. Leaves nothing running on
        the host, also when it raises or is interrupted. Raises `XEnvError`
        when the transport fails; the remote exit status is never guessed."""


def connect(host: str) -> Transport:
    """Rex now; ssh later. `host` is a Rex host label or server address."""
    from .rex import RexTransport

    return RexTransport(host)


def forward(host: str, command: str, argv: Sequence[str], stdout: TextIO, stderr: TextIO) -> int:
    """Run `x-env <argv>` on `host`; `command` names the session for the
    user. Writes the remote stdout to `stdout`, every other line to
    `stderr`, and returns the remote exit status."""
    result = connect(host).run(f"x-env {command}", ["x-env", "--forwarded", *argv])
    out, err = split_output(result.output)
    if result.exit_code == _COMMAND_NOT_FOUND and not _came_from_x_env(result.output):
        raise XEnvError(
            f"x-env is not installed on {host}: {' '.join(err).strip() or 'command not found'}. "
            f"Run `<x plugin folder>/tools/x-env/x-env install` on {host} once."
        )
    for line in err:
        print(line, file=stderr)
    for line in out:
        print(line, file=stdout)
    return result.exit_code


def split_output(text: str) -> tuple[list[str], list[str]]:
    """Mixed output -> (stdout lines without the marker, every other line)."""
    out: list[str] = []
    err: list[str] = []
    for line in text.splitlines():
        if line.startswith(STDOUT_MARKER):
            out.append(line.removeprefix(STDOUT_MARKER))
        else:
            err.append(line)
    return out, err


def _came_from_x_env(text: str) -> bool:
    return any(line.startswith((STDOUT_MARKER, "x-env: ")) for line in text.splitlines())


@contextlib.contextmanager
def marked_stdout() -> Iterator[None]:
    """The remote side: start each line written to `sys.stdout` with
    `STDOUT_MARKER`, and end an unfinished last line when the block ends."""
    original = sys.stdout
    marked = _MarkedLines(original)
    sys.stdout = marked
    try:
        yield
    finally:
        sys.stdout = original
        marked.finish()


class _MarkedLines(io.TextIOBase):
    def __init__(self, target: TextIO) -> None:
        self._target = target
        self._pending = ""

    def write(self, text: str) -> int:
        *lines, self._pending = (self._pending + text).split("\n")
        for line in lines:
            self._target.write(f"{STDOUT_MARKER}{line}\n")
        self._target.flush()
        return len(text)

    def finish(self) -> None:
        if self._pending:
            self._target.write(f"{STDOUT_MARKER}{self._pending}\n")
            self._pending = ""
        self._target.flush()
