"""Session lifecycle: start, run, hooks, wait, stop.

The flow has three processes, and each writes only its own part of the record:

  1. `start` (in `x-env agent|chief|run`): checks the harness, creates the
     record (session.json), and asks the terminal to run
     `x-env _session --terminal <name> <record>`. Returns at once.
  2. `run` (in `x-env _session`, inside the tab or the background process):
     appends `started`, runs the harness as a child, appends `exited` with the
     child's exit status, and exits with it. It is the only writer of
     `started` and `exited`, so every session that started also ends with an
     `exited` event unless the runner itself is killed with SIGKILL.
  3. `on_hook` (in `x-env _hook <harness> <record> <event> [<args>...]`,
     called by the harness): the adapter reads the payload and turns it
     into facts; `on_hook` writes turn events,
     last-turn.md, and the binding.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time
import traceback
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

from . import ENTRY, harness as harnesses, records, terminal as terminals
from .harness import Bound, Command, TurnBegan, TurnFinished
from .model import (
    Access,
    Effort,
    HarnessName,
    SessionName,
    Task,
    UsageError,
    WorktreeTask,
    XEnvError,
    terminal_label,
)
from .records import Exited, Finished, LaunchFacts, Lost, Prepared, SessionRecord, Started, TurnStarted
from .terminal.none import NoTerminal

log = logging.getLogger("x_env")

START_TIMEOUT_S = 60.0  # `wait`: a runner that has not written `started` by then never will
STOP_TIMEOUT_S = 15.0  # `stop_task`: how long a stopped session may take to write `exited`


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
    when a visible session was asked for and falls back. A headless session
    needs a prompt; that is checked before any record exists.
    """
    harness = harnesses.get(spec.harness)
    harness.check()
    term = NoTerminal() if spec.headless else terminals.detect()
    if not term.visible and spec.prompt is None:
        raise UsageError("A headless session needs --prompt. No session was created.")
    if not spec.headless and not term.visible:
        log.info("No Rex server; the session runs headless.")
    facts = LaunchFacts(
        harness=spec.harness,
        model=spec.model or harness.default_model(),
        effort=spec.effort,
        access=spec.access or default_access,
        mode="visible" if term.visible else "headless",
        host=host,
        cwd=task.source,
        prompt=spec.prompt,
        binding=harness.initial_binding(task.source),
    )
    record = records.create(task, spec.name, facts, _now())
    try:
        term.open(terminal_label(task.project_name, record.id), task.source, runner_argv(record, term.name))
    except XEnvError as error:
        raise XEnvError(f"{error} The record {record.id} was created, but the session never started.") from error
    return record


# --- The runner (`x-env _session`) ---------------------------------------------------


def run(record: SessionRecord, terminal: str) -> int:
    """The runner. Exit status = the harness's exit status.

    Writes `Started(pid=os.getpid(), terminal=..., handle=...)`, runs
    `harness.command(meta, hook_argv(record))` as a child in its own process
    group (headless: stdin /dev/null, stdout+stderr to output.log; visible:
    the child gets the terminal's foreground), forwards SIGTERM/SIGHUP to the
    child, then writes `Exited`. A launch that fails after `started` still
    writes `exited` (127: the harness CLI is missing; 1: another error).
    """
    meta = record.meta()
    visible = meta.launch.mode == "visible"
    if not visible:
        _redirect_output(record.output_path)
    forwarder = _Forwarder()
    for signum in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, forwarder.handle)
    pid = os.getpid()
    record.append(Started(
        at=_now(), pid=pid, process_start=records.process_start_time(pid) or "",
        terminal=terminal, terminal_handle=terminals.get(terminal).handle(os.environ),
    ))
    try:
        command = harnesses.get(meta.launch.harness).command(meta, hook_argv(record, meta.launch.harness))
        exit_code = _run_child(command, meta.launch.cwd, visible, forwarder)
    except Exception as error:  # the runner's one promise: `exited` follows `started`
        _report(f"x-env: The session could not run: {error}")
        exit_code = 127 if isinstance(error, FileNotFoundError) else 1
    record.append(Exited(at=_now(), exit_code=exit_code))
    return exit_code


class _Forwarder:
    """Forwards a stop signal to the child's process group. A signal that
    arrives before the child exists is forwarded right after it starts."""

    def __init__(self) -> None:
        self.child: subprocess.Popen[bytes] | None = None
        self.received: int | None = None

    def handle(self, signum: int, frame: object) -> None:
        self.received = signum
        if self.child is not None:
            _signal_group(self.child.pid, signum)


def _run_child(command: Command, cwd: Path, visible: bool, forwarder: _Forwarder) -> int:
    env = {**os.environ, **command.env}
    if visible and os.isatty(0):
        child = subprocess.Popen(command.argv, cwd=cwd, env=env, preexec_fn=_child_takes_terminal)
    else:
        stdin = None if visible else subprocess.DEVNULL
        child = subprocess.Popen(command.argv, cwd=cwd, env=env, stdin=stdin, process_group=0)
    forwarder.child = child
    if forwarder.received is not None:
        _signal_group(child.pid, forwarder.received)
    code = child.wait()
    if visible and os.isatty(0):
        _set_foreground()  # back to the runner's group
    return 128 - code if code < 0 else code


def _child_takes_terminal() -> None:
    """In the child, before exec: its own process group, which becomes the
    terminal's foreground group, so the harness can read the keyboard."""
    os.setpgid(0, 0)
    _set_foreground()


def _set_foreground() -> None:
    """Make the caller's process group the terminal's foreground group.
    SIGTTOU is ignored meanwhile, because a background group may not do this."""
    previous = signal.signal(signal.SIGTTOU, signal.SIG_IGN)
    try:
        os.tcsetpgrp(0, os.getpgrp())
    finally:
        signal.signal(signal.SIGTTOU, previous)


def _signal_group(pid: int, signum: int) -> None:
    try:
        os.killpg(pid, signum)
    except ProcessLookupError:
        try:
            os.kill(pid, signum)  # the child has not made its group yet
        except ProcessLookupError:
            pass


def _report(message: str) -> None:
    """Print to the runner's stderr: output.log, or the tab. A tab that Rex
    already closed is not an error."""
    try:
        print(message, file=sys.stderr, flush=True)
    except OSError:
        pass


def _redirect_output(path: Path) -> None:
    """Point the runner's stdout and stderr at output.log, so the child and
    the runner's own errors land there."""
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o644)
    os.dup2(descriptor, 1)
    os.dup2(descriptor, 2)
    os.close(descriptor)


# --- Hooks (`x-env _hook`) ---------------------------------------------------------------


def on_hook(
    record: SessionRecord, harness: HarnessName, event: str, args: Sequence[str], stdin: TextIO
) -> None:
    """Let the adapter read the hook call (Claude: stdin; Codex: the last
    argument) and apply the facts it reports. Never raises into the harness:
    a failure is logged to `<record>/hook-error.log` and the hook exits 0, so
    a broken record never blocks the agent."""
    try:
        for fact in harnesses.get(harness).parse_hook(event, args, stdin):
            match fact:
                case TurnBegan():
                    record.append(TurnStarted(_now()))
                case TurnFinished(text):
                    record.set_last_turn(text)
                    record.append_turn_end(_now())
                case Bound(binding):
                    record.bind(binding)
    except Exception:  # the hook's one promise: never fail the agent
        _log_hook_error(record, event)


def _log_hook_error(record: SessionRecord, event: str) -> None:
    try:
        with open(record.path / "hook-error.log", "a") as log_file:
            log_file.write(f"{_now().isoformat()} {event}\n{traceback.format_exc()}\n")
    except OSError:
        pass


# --- Wait and stop ----------------------------------------------------------------------


def wait(record: SessionRecord, host: str, poll_s: float = 1.0) -> int:
    """Block until the record's status is `Finished` (return its exit code)
    or `Lost` (raise "The session's runner is gone without an exit event").
    A record that stays `Prepared` for `START_TIMEOUT_S` raises too."""
    created_at = record.meta().created_at
    while True:
        match record.status(host):
            case Finished(exited):
                return exited.exit_code
            case Lost():
                raise XEnvError(f"The session's runner is gone without an exit event: {record.id}")
            case Prepared() if (_now() - created_at).total_seconds() > START_TIMEOUT_S:
                raise XEnvError(f"The session's runner never started: {record.id}")
        time.sleep(poll_s)


def stop_task(task: WorktreeTask, host: str, poll_s: float = 0.2) -> bool:
    """Stop every `Running` session of the task through the terminal named in
    its `Started` event, and wait until each writes `exited`. Returns True if
    any was running. Passed to `workspace.delete_task` as `stop_sessions`.

    A session recorded on another host is skipped: its process is not here.
    Raises `XEnvError` when a session does not stop within `STOP_TIMEOUT_S`.
    """
    stopping: list[SessionRecord] = []
    for record in records.list_sessions(task.project.sessions_dir, task.name):
        status = record.status(host)
        if not isinstance(status, records.Running):
            continue
        if record.meta().launch.host != host:
            log.info("Skipping session %s: it runs on host %s.", record.id, record.meta().launch.host)
            continue
        log.info("Stopping session %s", record.id)
        terminals.get(status.started.terminal).stop(status.started.pid, status.started.terminal_handle)
        stopping.append(record)
    deadline = time.monotonic() + STOP_TIMEOUT_S
    for record in stopping:
        while isinstance(record.status(host), records.Running):
            if time.monotonic() > deadline:
                raise XEnvError(f"Session {record.id} did not stop within {STOP_TIMEOUT_S:.0f} s.")
            time.sleep(poll_s)
    return bool(stopping)


# --- Commands for the terminal and the harness --------------------------------------------


def runner_argv(record: SessionRecord, terminal: str) -> list[str]:
    """`[python, <x-env entry>, "_session", "--terminal", <name>, <record path>]`.
    Absolute paths, so the command works in any shell and any terminal."""
    return [sys.executable, str(ENTRY), "_session", "--terminal", terminal, str(record.path)]


def hook_argv(record: SessionRecord, harness: HarnessName) -> list[str]:
    """`[python, <x-env entry>, "_hook", <harness>, <record path>]`. The
    adapter appends the hook event name."""
    return [sys.executable, str(ENTRY), "_hook", harness.value, str(record.path)]


def _now() -> datetime:
    return datetime.now(timezone.utc)
