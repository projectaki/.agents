"""Session lifecycle: start, run, hooks, wait, stop. Not in step 1.

The flow has three processes, and each writes only its own part of the record:

  1. `start` (in `x-env agent|chief|run`): checks the harness, creates the
     record (session.json), and asks the terminal to run
     `x-env _session <record>`. Returns at once.
  2. `run` (in `x-env _session`, inside the tab or the background process):
     appends `started`, runs the harness as a child, appends `exited` with the
     child's exit status, and exits with it. It is the only writer of
     `started` and `exited`, so every session that started also ends with an
     `exited` event unless the runner itself is killed with SIGKILL.
  3. `on_hook` (in `x-env _hook <harness> <record> <event>`, called by the
     harness): parses the payload with the adapter and writes turn events,
     last-turn.md, and the binding.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from . import harness as harnesses
from . import records, terminal as terminals
from .model import Access, Effort, HarnessName, SessionName, Task, WorktreeTask
from .records import SessionRecord


@dataclass(frozen=True)
class SessionSpec:
    """What `agent`, `chief`, and `run` ask for. Parsed from CLI options."""

    harness: HarnessName
    name: SessionName
    prompt: str | None
    model: str | None  # None: the adapter's default
    effort: Effort | None
    access: Access | None  # None: this host's default from config
    headless: bool  # `run --headless`; otherwise visible if a terminal can show it


def start(task: Task, spec: SessionSpec, *, host: str, default_access: Access) -> SessionRecord:
    """Create the record and launch the runner. Returns the record.

    The terminal is `NoTerminal` for `spec.headless`, else `detect()`;
    mode = "visible" if terminal.visible else "headless".
    The one line "x-env: No Rex server; the session runs headless." is logged
    when a visible session was asked for and falls back.
    """
    # TODO:
    #   h = harnesses.get(spec.harness); h.check()
    #   term = terminals.NoTerminal() if spec.headless else terminals.detect()
    #   facts = LaunchFacts(..., binding=h.initial_binding(task.source))
    #   record = records.create(task, spec.name, facts, now())
    #   term.open(terminal_label(task.project_name, record.id), task.source, runner_argv(record))
    raise NotImplementedError


def run(record: SessionRecord) -> int:
    """The runner. Exit status = the harness's exit status.

    Writes `Started(pid=os.getpid(), terminal=..., handle=$REX_SESSION)`,
    runs `harness.command(meta, hook_argv(record))` as a child in its own
    process group (headless: stdin /dev/null, stdout+stderr to output.log),
    forwards SIGTERM/SIGHUP to the child, then writes `Exited`.
    """
    raise NotImplementedError


def on_hook(record: SessionRecord, harness: HarnessName, payload: Mapping[str, object]) -> None:
    """Apply what a hook reports. Never raises into the harness: a failure is
    logged to `<record>/hook-error.log` and the hook exits 0, so a broken
    record never blocks the agent."""
    # TODO: for fact in harnesses.get(harness).parse_hook(payload):
    #   TurnBegan -> record.append(TurnStarted(now))
    #   TurnFinished(text) -> record.set_last_turn(text); record.append_turn_end(now)
    #   Bound(b) -> record.bind(b)
    raise NotImplementedError


def wait(record: SessionRecord, poll_s: float = 1.0) -> int:
    """Block until the record's status is `Finished` (return its exit code)
    or `Lost` (raise "The session's runner is gone without an exit event")."""
    raise NotImplementedError


def stop_task(task: WorktreeTask) -> bool:
    """Stop every `Running` session of the task through the terminal named in
    its `Started` event. Returns True if any was running. Passed to
    `workspace.delete_task` as `stop_sessions`."""
    raise NotImplementedError


def runner_argv(record: SessionRecord) -> list[str]:
    """`[python, <x-env entry>, "_session", <record path>]`. Absolute paths,
    so the command works in any shell and any terminal."""
    raise NotImplementedError


def hook_argv(record: SessionRecord, harness: HarnessName) -> list[str]:
    """`[python, <x-env entry>, "_hook", <harness>, <record path>]`. The
    adapter appends the hook event name."""
    raise NotImplementedError

