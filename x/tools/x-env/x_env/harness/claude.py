"""Claude Code adapter.

Tested facts (grounding): `claude -p "<prompt>" --session-id <uuid>
--model <model>`; the x plugin is installed (`x@<marketplace>` in
`~/.claude/plugins/installed_plugins.json`), so it loads without
`--plugin-dir`; transcript at `~/.claude/projects/<slug>/<session id>.jsonl`,
slug = cwd with `/` and `.` replaced by `-`; `--settings <json>` adds hooks
for one launch, and each hook gets its payload as JSON on stdin. Access as fx
passed it (`fx/agents/claude_access.py`): `auto` -> `--permission-mode auto`;
`full` -> `--permission-mode bypassPermissions` and the sandbox disabled.
"""

from __future__ import annotations

import json
import shlex
import shutil
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any, TextIO

from ..model import Access, HarnessName, XEnvError
from ..records import HarnessBinding, SessionMeta
from . import Command, HookFact, TurnBegan, TurnFinished

HOOK_EVENTS = ("UserPromptSubmit", "Stop")
_PERMISSION_MODE = {Access.AUTO: "auto", Access.FULL: "bypassPermissions"}


def transcript_path(home: Path, cwd: Path, session_id: str) -> Path:
    """Pure. `<home>/.claude/projects/<slug>/<session_id>.jsonl`."""
    slug = str(cwd).replace("/", "-").replace(".", "-")
    return home / ".claude" / "projects" / slug / f"{session_id}.jsonl"


def is_trusted(config: object, folder: Path) -> bool:
    """Pure. True when `folder` or a parent has `hasTrustDialogAccepted: true`
    in the parsed `~/.claude.json` (`{"projects": {"<path>": {...}}}`)."""
    projects = config.get("projects") if isinstance(config, dict) else None
    if not isinstance(projects, dict):
        return False
    return any(
        isinstance(projects.get(str(path)), dict) and projects[str(path)].get("hasTrustDialogAccepted") is True
        for path in (folder, *folder.parents)
    )


def has_x_plugin(installed: object) -> bool:
    """Pure. True when the parsed `installed_plugins.json`
    (`{"plugins": {"<plugin>@<marketplace>": [<install>, ...]}}`) lists an
    install of the plugin `x` from any marketplace."""
    plugins = installed.get("plugins") if isinstance(installed, dict) else None
    if not isinstance(plugins, dict):
        return False
    return any(key.partition("@")[0] == "x" and installs for key, installs in plugins.items())


def x_plugin_installed(home: Path) -> bool:
    """Reads `<home>/.claude/plugins/installed_plugins.json`, never writes it.
    A missing or unreadable file, or bad JSON, counts as not installed."""
    try:
        installed = json.loads((home / ".claude" / "plugins" / "installed_plugins.json").read_text())
    except (OSError, ValueError):
        return False
    return has_x_plugin(installed)


def folder_is_trusted(home: Path, folder: Path) -> bool:
    """Reads `<home>/.claude.json`, never writes it. A missing or unreadable
    file, or bad JSON, counts as not trusted."""
    try:
        config = json.loads((home / ".claude.json").read_text())
    except (OSError, ValueError):
        return False
    return is_trusted(config, folder)


class Claude:
    name = HarnessName.CLAUDE

    def check(self) -> None:
        if shutil.which("claude") is None:
            raise XEnvError("The claude CLI is not on PATH. No session was created.")
        if not x_plugin_installed(Path.home()):
            raise XEnvError(
                "The x plugin is not installed in Claude Code. Install it with "
                "`claude plugin install x@<marketplace>`. No session was created."
            )

    def default_model(self) -> str:
        return "opus"

    def initial_binding(self, cwd: Path) -> HarnessBinding:
        session_id = str(uuid.uuid4())
        return HarnessBinding(session_id, transcript_path(Path.home(), cwd, session_id))

    def command(self, meta: SessionMeta, hook: Sequence[str]) -> Command:
        launch = meta.launch
        if launch.binding is None:
            raise XEnvError(f"The Claude session has no session id: {meta.id}")
        settings: dict[str, Any] = {
            "hooks": {
                event: [{"hooks": [{"type": "command", "command": shlex.join([*hook, event])}]}]
                for event in HOOK_EVENTS
            }
        }
        if launch.access is Access.FULL:
            settings["sandbox"] = {"enabled": False}
        argv = [
            "claude",
            "--session-id", launch.binding.session_id,
            "--model", launch.model,
            "--settings", json.dumps(settings),
            "--permission-mode", _PERMISSION_MODE[launch.access],
        ]
        if launch.effort is not None:
            argv += ["--effort", launch.effort]
        if launch.mode == "headless":
            argv.append("-p")
        if launch.prompt is not None:
            argv += ["--", launch.prompt]  # `--`: a prompt that starts with `-` stays a prompt
        return Command(argv=tuple(argv), env={})

    def parse_hook(self, event: str, args: Sequence[str], stdin: TextIO) -> list[HookFact]:
        """The payload is a JSON object on stdin; `event` fills
        `hook_event_name` if the payload lacks it. UserPromptSubmit ->
        TurnBegan. Stop -> TurnFinished, once per turn: a Stop with
        `stop_hook_active` true continues a turn that a Stop hook held open.
        Subagent payloads (`agent_id`) and other events -> []."""
        payload = json.loads(stdin.read())
        if not isinstance(payload, dict):
            raise ValueError(f"Expected a JSON object, got {type(payload).__name__}")
        payload.setdefault("hook_event_name", event)
        if payload.get("agent_id"):
            return []
        match payload.get("hook_event_name"):
            case "UserPromptSubmit":
                return [TurnBegan()]
            case "Stop" if payload.get("stop_hook_active") is not True:
                message = payload.get("last_assistant_message")
                return [TurnFinished(message if isinstance(message, str) else "")]
        return []
