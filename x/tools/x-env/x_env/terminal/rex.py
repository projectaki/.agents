"""Rex: a session the user can watch and type in.

`rex --autostart=false new <label> --cwd <dir> --keep-open --json -- <argv>`.
Rex runs the argv directly in the user's login environment, so the runner is
the session's process. Inside, REX_SESSION is set, and the runner stores it
in the `Started` event as the handle. `rex kill <handle>` sends the runner
SIGHUP; the runner forwards it to the harness and then writes `exited`.

Every call passes `--autostart=false`, so x-env never starts a Rex server.
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

from ..model import XEnvError

_NOT_FOUND = 3  # `rex kill` exit status for an unknown session (tested)


class Rex:
    name = "rex"
    visible = True

    def open(self, label: str, cwd: Path, argv: Sequence[str]) -> None:
        result = _rex("new", label, "--cwd", str(cwd), "--keep-open", "--json", "--", *argv)
        if result.returncode != 0:
            raise XEnvError(f"Could not open a Rex session: {result.stderr.strip()}")

    def handle(self, env: Mapping[str, str]) -> str | None:
        return env.get("REX_SESSION") or None

    def stop(self, pid: int, handle: str | None) -> None:
        if handle is None:
            raise XEnvError(f"The Rex session of process {pid} has no recorded handle.")
        result = _rex("kill", handle)
        if result.returncode not in (0, _NOT_FOUND):
            raise XEnvError(f"Could not stop Rex session {handle}: {result.stderr.strip()}")


def _rex(*arguments: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["rex", "--autostart=false", *arguments],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise XEnvError(f"Could not run rex: {error}") from error
