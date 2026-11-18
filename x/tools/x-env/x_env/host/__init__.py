"""Host adapters: run the same x-env command on another machine.

The core never runs ssh. `cli` forwards the whole command before it parses
anything else, so the remote x-env does all the work with its own config,
its own git, and its own terminal.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from ..config import HostConfig


class Host(Protocol):
    def forward(self, argv: Sequence[str]) -> int:
        """Run `x-env <argv>` on the host. Return its exit status.

        Callers need the remote stdout (a task path, a session id). See the
        open question in rationale.md: `rex run --wait` runs the command in a
        new block and returns only the exit status.
        """


def connect(config: HostConfig) -> Host:
    """By `config.transport`: "rex" now, "ssh" later."""
    from .rex import RexHost

    return {"rex": RexHost}[config.transport](config.target)
