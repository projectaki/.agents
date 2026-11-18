"""Claude Code adapter.

Tested facts (grounding): `claude -p "<prompt>" --plugin-dir <dir>
--session-id <uuid> --model <model>`; transcript at
`~/.claude/projects/<slug>/<session id>.jsonl`, slug = cwd with `/` and `.`
replaced by `-`; `--settings <json>` adds hooks for one launch.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ..model import HarnessName
from ..records import HarnessBinding, SessionMeta
from . import Command, HookFact


def transcript_path(home: Path, cwd: Path, session_id: str) -> Path:
    """Pure. `<home>/.claude/projects/<slug>/<session_id>.jsonl`."""
    raise NotImplementedError


class Claude:
    name = HarnessName.CLAUDE

    def check(self) -> None:
        raise NotImplementedError

    def default_model(self) -> str:
        raise NotImplementedError

    def initial_binding(self, cwd: Path) -> HarnessBinding:
        # TODO: uuid4(); HarnessBinding(id, transcript_path(Path.home(), cwd, id))
        raise NotImplementedError

    def command(self, meta: SessionMeta, hook: Sequence[str]) -> Command:
        # TODO:
        #   settings = {"hooks": {ev: [{"hooks": [{"type": "command",
        #       "command": shlex.join([*hook, ev])}]}] for ev in
        #       ("UserPromptSubmit", "Stop")}}
        #   argv = ["claude", "--session-id", binding.session_id, "--model", model,
        #           "--settings", json.dumps(settings), "--plugin-dir", <x plugin>]
        #   + effort flag, + access flags (FULL -> bypass permissions)
        #   headless: [..., "-p", prompt]; visible: [..., prompt] if prompt
        raise NotImplementedError

    def parse_hook(self, payload: Mapping[str, object]) -> list[HookFact]:
        # TODO: agent_id set -> []
        #   UserPromptSubmit -> [TurnBegan()]
        #   Stop -> [TurnFinished(payload["last_assistant_message"])]
        raise NotImplementedError
