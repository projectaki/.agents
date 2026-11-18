"""Codex adapter.

Tested facts (grounding, codex-cli 0.169.0): `codex exec --skip-git-repo-check
-C <dir> "<prompt>" </dev/null` runs headless and prints `session id: <id>`;
`codex [options] -- "<prompt>"` opens the interactive UI with that first
message. `-c 'notify=["<cmd>", ...]'` sets a turn-complete command for one
launch, and Codex appends one JSON argument:
`{"type": "agent-turn-complete", "thread-id", "turn-id", "cwd", "client",
"input-messages", "last-assistant-message"}`. There is no turn-start event:
hooks would need `--dangerously-bypass-hook-trust`, which x-env does not use.
The transcript is `~/.codex/sessions/<yyyy>/<mm>/<dd>/rollout-<time>-<thread-id>.jsonl`;
its first line is `{"type": "session_meta", "payload": {"thread_source": ...}}`,
`"user"` for the main thread (exec and the UI) and `"subagent"` for a
subagent. Notify also fires for threads that are not the session's own: in
the UI, a title-generation thread with its own `thread-id` and no rollout
file.
The x plugin is installed (`[plugins."x@<marketplace>"]` in
`~/.codex/config.toml`), so it loads by itself. Access as fx passed it
(`fx/agents/codex_access.py`): `auto` -> `--approve-for-me`; `full` ->
`--dangerously-bypass-approvals-and-sandbox`.
"""

from __future__ import annotations

import json
import re
import shutil
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from ..model import Access, HarnessName, XEnvError
from ..records import HarnessBinding, SessionMeta
from . import Bound, Command, HookFact, TurnFinished

DEFAULT_MODEL = "default"
"""Recorded when neither `--model` nor `~/.codex/config.toml` names a model."""

_ACCESS_FLAG = {Access.AUTO: "--approve-for-me", Access.FULL: "--dangerously-bypass-approvals-and-sandbox"}
_THREAD_ID = re.compile(r"[A-Za-z0-9-]+")  # also keeps glob characters out of `find_transcript`


def read_config(home: Path) -> dict[str, object]:
    """Parse `<home>/.codex/config.toml`, never write it. A missing or
    unreadable file, or bad TOML, reads as empty."""
    try:
        return tomllib.loads((home / ".codex" / "config.toml").read_text())
    except (OSError, ValueError):
        return {}


def is_trusted(config: dict[str, object], folder: Path) -> bool:
    """Pure. True when `[projects."<path>"]` has `trust_level = "trusted"` for
    `folder` as given or resolved. Codex trusts a folder, not its parents."""
    projects = config.get("projects")
    if not isinstance(projects, dict):
        return False
    return any(
        isinstance(projects.get(str(path)), dict) and projects[str(path)].get("trust_level") == "trusted"
        for path in (folder, folder.resolve())
    )


def folder_is_trusted(home: Path, folder: Path) -> bool:
    """Reads `<home>/.codex/config.toml`, never writes it. A missing or
    unreadable file, or bad TOML, counts as not trusted."""
    return is_trusted(read_config(home), folder)


def has_x_plugin(config: dict[str, object]) -> bool:
    """Pure. True when the config has `[plugins."x@<marketplace>"]` from any
    marketplace, not `enabled = false`."""
    plugins = config.get("plugins")
    if not isinstance(plugins, dict):
        return False
    return any(
        key.partition("@")[0] == "x" and isinstance(entry, dict) and entry.get("enabled", True) is not False
        for key, entry in plugins.items()
    )


def configured_model(config: dict[str, object]) -> str:
    """Pure. The config's top-level `model`, else `DEFAULT_MODEL`."""
    model = config.get("model")
    return model if isinstance(model, str) and model else DEFAULT_MODEL


def find_transcript(home: Path, thread_id: str) -> Path | None:
    """The rollout file of `thread_id` under `<home>/.codex/sessions`, or None
    when there is none. `thread_id` must match `_THREAD_ID`."""
    matches = sorted((home / ".codex" / "sessions").glob(f"*/*/*/rollout-*-{thread_id}.jsonl"))
    return matches[0] if matches else None


def is_user_thread(rollout: Path) -> bool:
    """True when the rollout's first line is a `session_meta` with
    `thread_source` "user". An unreadable file or line counts as False."""
    try:
        with rollout.open() as file:
            meta = json.loads(file.readline())
        return meta["type"] == "session_meta" and meta["payload"]["thread_source"] == "user"
    except (OSError, ValueError, KeyError, TypeError):
        return False


class Codex:
    name = HarnessName.CODEX

    def check(self) -> None:
        if shutil.which("codex") is None:
            raise XEnvError("The codex CLI is not on PATH. No session was created.")
        if not has_x_plugin(read_config(Path.home())):
            raise XEnvError(
                "The x plugin is not installed in Codex. Install it with "
                "`codex plugin add x@<marketplace>`. No session was created."
            )

    def default_model(self) -> str:
        return configured_model(read_config(Path.home()))

    def initial_binding(self, cwd: Path) -> None:
        """Codex chooses its own id; the first notify payload reports it."""
        return None

    def command(self, meta: SessionMeta, hook: Sequence[str]) -> Command:
        """Headless: `codex exec --skip-git-repo-check ... -- <prompt>`.
        Visible: `codex ... [-- <prompt>]`. The model is passed unless it is
        `DEFAULT_MODEL`, so Codex runs the model that the record names."""
        launch = meta.launch
        notify = json.dumps([*hook, "notify"], ensure_ascii=False)  # a JSON string array is a TOML array
        argv = ["codex", "exec", "--skip-git-repo-check"] if launch.mode == "headless" else ["codex"]
        argv += ["-C", str(launch.cwd), "-c", f"notify={notify}", _ACCESS_FLAG[launch.access]]
        if launch.model != DEFAULT_MODEL:
            argv += ["-m", launch.model]
        if launch.effort is not None:
            argv += ["-c", f'model_reasoning_effort="{launch.effort}"']
        if launch.prompt is not None:
            argv += ["--", launch.prompt]  # `--`: a prompt that starts with `-` stays a prompt
        return Command(argv=tuple(argv), env={})

    def parse_hook(self, event: str, args: Sequence[str], stdin: TextIO) -> list[HookFact]:
        """The payload is the last argument; stdin is not read (in a visible
        session it is the terminal). An `agent-turn-complete` of a user
        thread (a rollout file with `thread_source` "user") -> Bound to that
        thread, then TurnFinished. `sessions` applies them in order, so a
        payload from another user thread fails the bind and adds no turn.
        Other types, and threads that are not user threads (title
        generation, subagents) -> []."""
        if not args:
            raise ValueError("The notify call has no payload argument")
        payload = json.loads(args[-1])
        if not isinstance(payload, dict):
            raise ValueError(f"Expected a JSON object, got {type(payload).__name__}")
        if payload.get("type") != "agent-turn-complete":
            return []
        thread_id = payload.get("thread-id")
        if not isinstance(thread_id, str) or not _THREAD_ID.fullmatch(thread_id):
            raise ValueError(f"The notify payload has no valid thread-id: {thread_id!r}")
        rollout = find_transcript(Path.home(), thread_id)
        if rollout is None or not is_user_thread(rollout):
            return []
        message = payload.get("last-assistant-message")
        return [
            Bound(HarnessBinding(thread_id, rollout)),
            TurnFinished(message if isinstance(message, str) else ""),
        ]
