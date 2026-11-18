"""Rex: a tab the user can watch and type in.

`rex new <label> --cwd <dir> --keep-open -- <argv>`; inside, REX_SESSION is
set, and the runner stores it in the `Started` event as the handle.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path


class Rex:
    name = "rex"
    visible = True

    def open(self, label: str, cwd: Path, argv: Sequence[str]) -> None:
        raise NotImplementedError

    def stop(self, pid: int, handle: str | None) -> None:
        # TODO: `rex kill <handle>`; a missing session is not an error.
        raise NotImplementedError
