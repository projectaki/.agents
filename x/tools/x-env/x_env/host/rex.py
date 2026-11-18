"""Forward a command through Rex: `rex -S <label> run --wait ... -- x-env ...`."""

from __future__ import annotations

from collections.abc import Sequence


class RexHost:
    def __init__(self, label: str) -> None:
        self.label = label

    def forward(self, argv: Sequence[str]) -> int:
        # TODO: rex -S <label> run --wait --focus=false --shell=none -- x-env <argv>
        #   Return the exit status. Output relay is an open question.
        raise NotImplementedError
