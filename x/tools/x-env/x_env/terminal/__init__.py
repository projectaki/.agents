"""Terminal adapters: where a session's process runs.

A terminal runs one argv in one folder and can stop it later. It knows
nothing about harnesses or records: the argv is always
`x-env _session <record>`, and that runner writes the records.

`detect()` decides once per command. A reachable Rex server gives `rex`;
otherwise `none`, and the CLI prints one line saying the session is headless.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol


class Terminal(Protocol):
    name: str
    visible: bool  # False: the session must run headless

    def open(self, label: str, cwd: Path, argv: Sequence[str]) -> None:
        """Start `argv` in `cwd` and return without waiting."""

    def stop(self, pid: int, handle: str | None) -> None:
        """Stop a session that this terminal started, from its `Started` event.
        A session that is already gone is not an error."""


def detect() -> Terminal:
    # TODO: Rex() if `rex --autostart=false ls -q` exits 0, else NoTerminal().
    #   `--autostart=false` matters: plain `rex ls` starts a local server.
    raise NotImplementedError


def get(name: str) -> Terminal:
    """By the name stored in a `Started` event, to stop that session later."""
    from .none import NoTerminal
    from .rex import Rex

    return {t.name: t for t in (NoTerminal(), Rex())}[name]
