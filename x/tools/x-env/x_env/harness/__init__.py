"""Harness adapters: how to launch one agent CLI and read its hooks.

A harness never writes records. It turns a launch into a command and a hook
payload into a `HookFact`; `sessions` does the writing. Adding a harness is one
new module and one line in `HARNESSES`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ..model import HarnessName
from ..records import HarnessBinding, SessionMeta


@dataclass(frozen=True)
class Command:
    """One harness launch. `env` holds only the variables to add or override."""

    argv: tuple[str, ...]
    env: Mapping[str, str]


# --- Facts that hooks report --------------------------------------------------------


@dataclass(frozen=True)
class TurnBegan:
    pass


@dataclass(frozen=True)
class TurnFinished:
    last_message: str


@dataclass(frozen=True)
class Bound:
    binding: HarnessBinding


HookFact = TurnBegan | TurnFinished | Bound


class Harness(Protocol):
    name: HarnessName

    def check(self) -> None:
        """Raise `XEnvError` when the CLI is missing, before any record exists."""

    def default_model(self) -> str: ...

    def initial_binding(self, cwd: Path) -> HarnessBinding | None:
        """The transcript location if x-env can choose it before launch.
        Claude: a new UUID passed as `--session-id`. Codex: None."""

    def command(self, meta: SessionMeta, hook: Sequence[str]) -> Command:
        """The argv for this launch. `hook` is the argv prefix of
        `x-env _hook <harness> <record>`; the adapter installs it for this one
        launch only (Claude: `--settings` JSON with UserPromptSubmit, Stop, and
        SessionStart hooks; Codex: `-c hooks...` or `-c notify=[...]`).
        Headless adds `-p` / `exec` and the prompt; visible passes the prompt
        as the first message."""

    def parse_hook(self, payload: Mapping[str, object]) -> list[HookFact]:
        """Turn one hook payload into facts. Ignores subagent events
        (`agent_id` set): subagents live in the parent's transcript."""


def _registry() -> dict[HarnessName, Harness]:
    from .claude import Claude
    from .codex import Codex

    return {h.name: h for h in (Claude(), Codex())}


def get(name: HarnessName) -> Harness:
    return _registry()[name]
