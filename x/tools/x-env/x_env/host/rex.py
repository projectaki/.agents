"""Run a command on another machine through its Rex server.

    rex --autostart=false -S <host> new <label> --keep-open --json -- <argv>
    rex --autostart=false -S <host> wait --json <block>      -> {"exit_code": n}
    rex --autostart=false -S <host> capture -s <session> --trim --unwrap
    rex --autostart=false -S <host> kill <session>           (always, in `finally`)

Rex runs the argv in the user's login environment (profile, not .bashrc).
`--keep-open` keeps the screen after the command exits, so `capture` can
read it; `wait` returns the child's status even so. stdout and stderr arrive
mixed in the capture; `host.split_output` separates them. Without `--cwd`,
Rex starts in the caller's folder when the host has it, else in home; the
forwarded x-env goes home itself, so it does not matter.

`wait --json` prints `exit_code` only when the command ended. Without it,
the transport failed (a lost connection), and the remote status is unknown.
"""

from __future__ import annotations

import json
import logging
import subprocess
from collections.abc import Sequence

from ..model import XEnvError
from . import Completed

log = logging.getLogger("x_env")
_NOT_FOUND = 3  # `rex kill` exit status for an unknown session (tested)


class RexTransport:
    def __init__(self, host: str) -> None:
        self.host = host

    def run(self, label: str, argv: Sequence[str]) -> Completed:
        created = self._rex("new", label, "--keep-open", "--json", "--", *argv)
        session, block = _parse_new(created.stdout)
        try:
            ended = self._rex("wait", "--json", block, check=False)  # it exits with the remote status
            exit_code = _parse_wait(ended.stdout)
            if exit_code is None:
                raise XEnvError(
                    f"Lost the Rex session on {self.host} before the command ended; "
                    f"its result is unknown: {_detail(ended)}"
                )
            screen = self._rex("capture", "-s", session, "--trim", "--unwrap")
            return Completed(exit_code, screen.stdout)
        finally:
            killed = self._rex("kill", session, check=False)
            if killed.returncode not in (0, _NOT_FOUND):  # warn only: an error here would hide the first one
                log.warning("Could not close Rex session %s on %s: %s. Close it with `rex -S %s kill %s`.",
                            session, self.host, _detail(killed), self.host, session)

    def _rex(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        """No timeout: `wait` lasts as long as the remote command."""
        argv = ["rex", "--autostart=false", "-S", self.host, *arguments]
        try:
            result = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True)
        except OSError as error:
            raise XEnvError(f"Could not run rex: {error}") from error
        if check and result.returncode != 0:
            raise XEnvError(f"rex {arguments[0]} on {self.host} failed: {_detail(result)}")
        return result


def _parse_new(stdout: str) -> tuple[str, str]:
    try:
        created = json.loads(stdout)
        return created["session_id"], created["initial_windows"][0]["block_ids"][0]
    except (ValueError, KeyError, IndexError, TypeError) as error:
        raise XEnvError(f"Unexpected output from rex new: {stdout.strip()!r}") from error


def _parse_wait(stdout: str) -> int | None:
    try:
        exit_code = json.loads(stdout.splitlines()[0]).get("exit_code")
    except (ValueError, IndexError, AttributeError):
        return None
    return exit_code if isinstance(exit_code, int) else None


def _detail(result: subprocess.CompletedProcess[str]) -> str:
    return (result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}").splitlines()[-1]
