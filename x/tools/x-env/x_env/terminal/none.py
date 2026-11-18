"""No terminal: a detached background process."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path


class NoTerminal:
    name = "none"
    visible = False

    def open(self, label: str, cwd: Path, argv: Sequence[str]) -> None:
        # TODO: Popen(argv, cwd=cwd, start_new_session=True,
        #   stdin/stdout/stderr=DEVNULL). The runner redirects the harness
        #   output to the record's output.log itself.
        raise NotImplementedError

    def stop(self, pid: int, handle: str | None) -> None:
        # TODO: os.killpg(pid, SIGTERM); ProcessLookupError -> already gone.
        raise NotImplementedError
