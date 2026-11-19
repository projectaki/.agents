"""Terminal adapters: where a session's process runs.

A terminal runs one argv in one folder and can stop it later. It knows
nothing about harnesses or records: the argv is always
`x-env _session --terminal <name> <record>`, and that runner writes the
records.

`detect()` decides once per command. A reachable Rex server gives `rex`;
otherwise `none`, and `sessions.start` logs one line saying the session is
headless.
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol


class Terminal(Protocol):
    name: str
    visible: bool  # False: the session must run headless

    def open(self, label: str, cwd: Path, argv: Sequence[str]) -> None:
        """Start `argv` in `cwd` and return without waiting. Raises
        `XEnvError` when the terminal cannot start it."""

    def handle(self, env: Mapping[str, str]) -> str | None:
        """Called by the runner, inside a session that this terminal started:
        the handle that `stop` needs, read from the runner's environment."""

    def stop(self, pid: int, handle: str | None) -> None:
        """Stop a session that this terminal started, from its `Started` event.
        A session that is already gone is not an error."""


def detect() -> Terminal:
    """`Rex()` if `rex --autostart=false ls -q` exits 0, else `NoTerminal()`.
    `--autostart=false` matters: plain `rex ls` starts a local server."""
    from .none import NoTerminal
    from .rex import Rex

    try:
        result = subprocess.run(
            ["rex", "--autostart=false", "ls", "-q"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return NoTerminal()
    return Rex() if result.returncode == 0 else NoTerminal()


def get(name: str) -> Terminal:
    """By the name stored in a `Started` event, to stop that session later."""
    from .none import NoTerminal
    from .rex import Rex

    return {t.name: t for t in (NoTerminal(), Rex())}[name]
