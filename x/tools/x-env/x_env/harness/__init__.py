"""Harness adapters: how to launch one agent CLI and read its hooks.

A harness never writes records. It turns a launch into a command and one hook
call into `HookFact`s; `sessions` does the writing. Adding a harness is one
new module and one line in `HARNESSES`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TextIO

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
        """Raise `XEnvError` before any record exists when the CLI is missing,
        or when the x plugin is not installed in this harness. Reads only."""

    def default_model(self) -> str:
        """The model to record when the caller names none."""

    def initial_binding(self, cwd: Path) -> HarnessBinding | None:
        """The transcript location if x-env can choose it before launch.
        Claude: a new UUID passed as `--session-id`. Codex: None."""

    def command(self, meta: SessionMeta, hook: Sequence[str]) -> Command:
        """The argv for this launch. `hook` is the argv prefix of
        `x-env _hook <harness> <record>`; the adapter installs it for this one
        launch only (Claude: `--settings` JSON with UserPromptSubmit and Stop
        hooks; Codex: `-c notify=[...]`).
        Headless adds `-p` / `exec` and the prompt; visible passes the prompt
        as the first message."""

    def parse_hook(self, event: str, args: Sequence[str], stdin: TextIO) -> list[HookFact]:
        """Read one hook call and turn its payload into facts. `event` is the
        name the adapter appended to the hook argv; `args` are the arguments
        the harness added after it; `stdin` is the hook's stdin, read only by
        an adapter whose harness writes the payload there (Claude reads stdin,
        Codex reads the last argument). Raises `ValueError` for a payload that
        does not parse. Ignores subagent events: subagents live in the
        parent's transcript."""


def _registry() -> dict[HarnessName, Harness]:
    from .claude import Claude
    from .codex import Codex

    return {h.name: h for h in (Claude(), Codex())}


def get(name: HarnessName) -> Harness:
    return _registry()[name]
