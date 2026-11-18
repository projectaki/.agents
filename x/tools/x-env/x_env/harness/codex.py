"""Codex adapter. Not in step 1.

Tested facts (grounding): `codex exec --skip-git-repo-check -C <dir> "<prompt>"`
prints `session id: <id>`; transcript at
`~/.codex/sessions/<yyyy>/<mm>/<dd>/rollout-<time>-<id>.jsonl`;
`-c notify=[...]` sets a turn-complete command for one launch; repo skills
load from `<dir>/.agents/skills/`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ..model import HarnessName
from ..records import HarnessBinding, SessionMeta
from . import Command, HookFact


class Codex:
    name = HarnessName.CODEX

    def check(self) -> None:
        raise NotImplementedError

    def default_model(self) -> str:
        raise NotImplementedError

    def initial_binding(self, cwd: Path) -> None:
        """Codex chooses its own id; the first hook payload reports it."""
        return None

    def command(self, meta: SessionMeta, hook: Sequence[str]) -> Command:
        raise NotImplementedError

    def parse_hook(self, payload: Mapping[str, object]) -> list[HookFact]:
        # TODO: SessionStart (or the first payload with session_id and
        #   transcript_path) -> [Bound(...)]; turn start -> TurnBegan;
        #   turn complete -> TurnFinished(last message).
        raise NotImplementedError
