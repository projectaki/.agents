"""No terminal: a detached background process."""

from __future__ import annotations

import os
import signal
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

from ..model import XEnvError


class NoTerminal:
    name = "none"
    visible = False

    def open(self, label: str, cwd: Path, argv: Sequence[str]) -> None:
        """A new process session, so it outlives the caller and its terminal.
        The runner redirects the harness output to the record's output.log."""
        try:
            subprocess.Popen(
                list(argv), cwd=cwd, start_new_session=True,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except OSError as error:
            raise XEnvError(f"Could not start the session runner: {error}") from error

    def handle(self, env: Mapping[str, str]) -> None:
        return None

    def stop(self, pid: int, handle: str | None) -> None:
        """SIGTERM to the runner's process group. The runner forwards it to
        the harness and then writes `exited`."""
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
