"""Session records: a harness-neutral index of each agent session.

Layout, per task (the folder outlives `x-env delete`):

    <task.records>/                    = <project>/sessions/<task>/
      .lock                            flock target for number allocation
      <nnn>-<name>/
        .lock          flock target for turn writes and `bind`
        session.json   launch facts; see SessionMeta
        events.jsonl   append-only; see Event
        last-turn.md   final assistant message of the latest turn
        output.log     headless only: the harness's stdout and stderr

Writers and what each owns (per separate-before-serializing-shared-state):

    create()                 x-env, before the harness starts   session.json
    append(Started/Exited)   the session runner (`x-env _session`)  events.jsonl
    append(TurnStarted), append_turn_end(), set_last_turn(), bind()
                             the harness hooks (`x-env _hook`)  events.jsonl,
                                                                last-turn.md,
                                                                session.json (once)
    output.log               the session runner, headless only

Concurrency rules, enforced here and nowhere else:
  - Numbers: `create` holds `flock(.lock)` while it picks max+1 and makes the
    folder. A crash releases the lock; there is nothing stale to clean.
  - events.jsonl: each event is one `os.write` of one line under
    `O_APPEND`, so lines from the runner and hooks never interleave. A reader
    skips a line that does not parse (a crash mid-write). A writer that finds
    a last line without "\\n" first writes "\\n", so the fragment stays a
    separate bad line and the next event is not merged into it.
  - Turn ends (count the turns, append turn_end) and `bind` run under
    `flock(<record>/.lock)`, so two hook calls cannot take one number.
  - last-turn.md and session.json: written to a temp file, then renamed.
  - `bind` is the only change to session.json after `create`. It fills an
    empty binding, and is a no-op when the value already matches.

The model never writes records. There is no findings file.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from .model import (
    Access,
    Effort,
    HarnessName,
    Mode,
    ProjectName,
    SessionId,
    SessionName,
    Task,
    TaskName,
    UsageError,
    XEnvError,
)

SCHEMA = 1
_FOLDER = re.compile(r"(\d{3,})-(.+)")


# --- session.json -------------------------------------------------------------------


@dataclass(frozen=True)
class HarnessBinding:
    """How to find the harness's own transcript for this session."""

    session_id: str
    transcript: Path


@dataclass(frozen=True)
class LaunchFacts:
    """What the caller decides before a session starts. Input to `create`."""

    harness: HarnessName
    model: str
    effort: Effort | None
    access: Access
    mode: Mode
    host: str  # this machine's host label, from config
    cwd: Path  # task.source
    prompt: str | None
    binding: HarnessBinding | None  # known up front for Claude, later for Codex


@dataclass(frozen=True)
class SessionMeta:
    """The parsed content of session.json. Field names are the JSON keys."""

    schema: int
    id: SessionId
    project: ProjectName
    task: TaskName
    name: SessionName
    created_at: datetime
    launch: LaunchFacts


# --- events.jsonl ----------------------------------------------------------------------


@dataclass(frozen=True)
class Started:
    at: datetime
    pid: int  # the session runner's process (its group leader)
    process_start: str  # the process start time from /proc/<pid>/stat; with
    # the pid, it identifies the process, so a reused pid is never stopped
    terminal: str  # "none" or "rex"
    terminal_handle: str | None  # REX_SESSION inside Rex; None for "none"


@dataclass(frozen=True)
class TurnStarted:
    at: datetime


@dataclass(frozen=True)
class TurnEnded:
    at: datetime
    turn: int  # 1-based; derived by `append_turn_end`, never passed in
    duration_s: float  # since this turn's TurnStarted, else the previous TurnEnded, else Started


@dataclass(frozen=True)
class Exited:
    at: datetime
    exit_code: int  # 128 + signal when the runner was killed by a signal


Event = Started | TurnStarted | TurnEnded | Exited
EventKind = Literal["started", "turn_started", "turn_end", "exited"]

_KINDS: dict[type, EventKind] = {
    Started: "started",
    TurnStarted: "turn_started",
    TurnEnded: "turn_end",
    Exited: "exited",
}
_TYPES: dict[str, type] = {kind: cls for cls, kind in _KINDS.items()}


# --- Status, derived from events --------------------------------------------------------


@dataclass(frozen=True)
class Prepared:
    """Folder exists; the runner has not started (or died before `started`)."""


@dataclass(frozen=True)
class Running:
    started: Started
    turns: int


@dataclass(frozen=True)
class Finished:
    exited: Exited
    turns: int


@dataclass(frozen=True)
class Lost:
    """`started` without `exited`, and the process is gone on this host."""

    started: Started
    turns: int


Status = Prepared | Running | Finished | Lost


# --- The record handle ----------------------------------------------------------------


@dataclass(frozen=True)
class SessionRecord:
    """A handle to one record folder. All reads and writes go through it."""

    path: Path

    @property
    def id(self) -> SessionId:
        return SessionId(f"{self.path.parent.name}/{self.path.name}")

    @property
    def meta_path(self) -> Path:
        return self.path / "session.json"

    @property
    def events_path(self) -> Path:
        return self.path / "events.jsonl"

    @property
    def last_turn_path(self) -> Path:
        return self.path / "last-turn.md"

    @property
    def output_path(self) -> Path:
        return self.path / "output.log"

    def meta(self) -> SessionMeta:
        """Parse session.json. Raises `XEnvError` naming the file when the JSON
        or the schema version is wrong (records are a boundary: later tools
        and other hosts read them)."""
        try:
            data = json.loads(self.meta_path.read_text())
            if data["schema"] != SCHEMA:
                raise XEnvError(f"Unsupported record schema {data['schema']!r}: {self.meta_path}")
            return _meta_from_json(data)
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise XEnvError(f"Unreadable session record: {self.meta_path} ({error})") from error

    def events(self) -> Iterator[Event]:
        """Parse events.jsonl in order. Skips lines that do not parse, such as
        a fragment that a crash left mid-write."""
        try:
            content = self.events_path.read_text()
        except FileNotFoundError:
            return
        for line in content.split("\n"):
            event = _event_from_line(line)
            if event is not None:
                yield event

    def status(self, this_host: str) -> Status:
        """Fold the events. `Lost` checks the process only when the record's
        host is `this_host`; otherwise a `started` without `exited` is
        `Running`."""
        started: Started | None = None
        turns = 0
        for event in self.events():
            match event:
                case Started():
                    started = event
                case TurnEnded():
                    turns += 1
                case Exited():
                    return Finished(event, turns)
        if started is None:
            return Prepared()
        if self.meta().launch.host == this_host and process_start_time(started.pid) != started.process_start:
            return Lost(started, turns)
        return Running(started, turns)

    def last_turn_end(self) -> datetime | None:
        """The time of the latest turn end, or None before the first one."""
        ends = [event.at for event in self.events() if isinstance(event, TurnEnded)]
        return ends[-1] if ends else None

    def append(self, event: Started | TurnStarted | Exited) -> None:
        """Append one event line. Turn ends go through `append_turn_end`."""
        _append_line(self.events_path, _event_to_line(event))

    def append_turn_end(self, at: datetime) -> TurnEnded:
        """Derive the turn number and duration from earlier events, append,
        and return the event. Holds the record lock, so two hook calls cannot
        take one number."""
        with _lock(self.path / ".lock"):
            turns = 0
            turn_started: datetime | None = None  # counts only after the latest TurnEnded
            last_end: datetime | None = None
            started_at: datetime | None = None
            for event in self.events():
                match event:
                    case TurnEnded():
                        turns += 1
                        last_end = event.at
                        turn_started = None
                    case TurnStarted():
                        turn_started = event.at
                    case Started():
                        started_at = event.at
            since = turn_started or last_end or started_at or self.meta().created_at
            ended = TurnEnded(at=at, turn=turns + 1, duration_s=round((at - since).total_seconds(), 3))
            _append_line(self.events_path, _event_to_line(ended))
        return ended

    def set_last_turn(self, text: str) -> None:
        """Replace last-turn.md (temp + rename)."""
        _replace_file(self.last_turn_path, text)

    def bind(self, binding: HarnessBinding) -> None:
        """Fill `launch.binding` once. Same value again: no-op. A different
        value: raise, because one record must point to one transcript."""
        with _lock(self.path / ".lock"):
            meta = self.meta()
            if meta.launch.binding == binding:
                return
            if meta.launch.binding is not None:
                raise XEnvError(
                    f"The session is already bound to {meta.launch.binding.session_id}: {self.id}"
                )
            bound = replace(meta, launch=replace(meta.launch, binding=binding))
            _replace_file(self.meta_path, _meta_to_json(bound))


# --- Create and find -----------------------------------------------------------------


def create(task: Task, name: SessionName, facts: LaunchFacts, now: datetime) -> SessionRecord:
    """Allocate `<nnn>-<name>` and write session.json.

    Under `flock(<task.records>/.lock)`:
      number = 1 + max(nnn of existing `<nnn>-*` folders, default 0)
      mkdir `<nnn>-<name>`; write session.json (temp + rename).
    A crash after mkdir leaves a folder without session.json. `find` and
    `list_sessions` skip it, and the next number is still unique.
    """
    if task.records.is_symlink():
        raise XEnvError(f"Expected a directory, not a symbolic link: {task.records}")
    task.records.mkdir(parents=True, exist_ok=True)
    with _lock(task.records / ".lock"):
        numbers = [int(m[1]) for p in task.records.iterdir() if (m := _FOLDER.fullmatch(p.name))]
        number = max(numbers, default=0) + 1
        record = SessionRecord(task.records / f"{number:03d}-{name}")
        record.path.mkdir()
        meta = SessionMeta(
            schema=SCHEMA,
            id=SessionId.of(task.name, number, name),
            project=task.project_name,
            task=task.name,
            name=name,
            created_at=now,
            launch=facts,
        )
        _replace_file(record.meta_path, _meta_to_json(meta))
    return record


def find(records_root: Path, ref: str) -> SessionRecord:
    """Resolve `<task>/<nnn>-<name>`, `<task>/<nnn>`, or an absolute record path
    under `records_root` (= `<project>/sessions`). Raises `UsageError` for a
    malformed ref and `XEnvError("Session not found: ...")`."""
    path = Path(ref)
    if path.is_absolute():
        if path.parent.parent != records_root:
            raise XEnvError(f"Session not found: {ref}")
        ref = f"{path.parent.name}/{path.name}"
    task, slash, folder = ref.partition("/")
    if not slash:
        raise UsageError(f"Invalid session id: {ref}. Use <task>/<nnn>-<name>.")
    if folder.isdigit():
        number = int(folder)
        candidates = [
            r for r in list_sessions(records_root, TaskName(task))
            if int(_FOLDER.fullmatch(r.path.name)[1]) == number
        ]
        if not candidates:
            raise XEnvError(f"Session not found: {ref}")
        return candidates[0]
    task_name, number, name = SessionId(ref).parse()
    record = SessionRecord(records_root / task_name / f"{number:03d}-{name}")
    if not record.meta_path.is_file():
        raise XEnvError(f"Session not found: {ref}")
    return record


def list_sessions(records_root: Path, task: TaskName | None = None) -> list[SessionRecord]:
    """Every record with a session.json, ordered by task, then number."""
    task_dirs = [records_root / task] if task is not None else sorted(records_root.glob("*/"))
    found: list[tuple[str, int, SessionRecord]] = []
    for task_dir in task_dirs:
        if not task_dir.is_dir():
            continue
        for path in task_dir.iterdir():
            match = _FOLDER.fullmatch(path.name)
            if match and (path / "session.json").is_file():
                found.append((task_dir.name, int(match[1]), SessionRecord(path)))
    return [record for _, _, record in sorted(found, key=lambda item: item[:2])]


def process_start_time(pid: int) -> str | None:
    """The start time of process `pid` (field 22 of /proc/<pid>/stat), or None
    when no such process exists. With the pid, it identifies one process."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
    except (FileNotFoundError, ProcessLookupError):
        return None
    return stat.rpartition(")")[2].split()[19]


def format_time(value: datetime) -> str:
    """UTC with milliseconds and `Z`, as the records files write times."""
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


# --- Files and serialization (private) -------------------------------------------------


@contextmanager
def _lock(path: Path) -> Iterator[None]:
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o644)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def _append_line(path: Path, line: str) -> None:
    descriptor = os.open(path, os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o644)
    try:
        size = os.fstat(descriptor).st_size
        torn = size > 0 and os.pread(descriptor, 1, size - 1) != b"\n"
        os.write(descriptor, (("\n" if torn else "") + line + "\n").encode())
    finally:
        os.close(descriptor)


def _replace_file(path: Path, content: str) -> None:
    temporary = path.parent / f".{path.name}.{secrets.token_hex(4)}.tmp"
    try:
        temporary.write_text(content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _event_to_line(event: Event) -> str:
    data: dict[str, Any] = {"event": _KINDS[type(event)], "at": format_time(event.at)}
    match event:
        case Started():
            data |= {
                "pid": event.pid,
                "process_start": event.process_start,
                "terminal": event.terminal,
                "terminal_handle": event.terminal_handle,
            }
        case TurnEnded():
            data |= {"turn": event.turn, "duration_s": event.duration_s}
        case Exited():
            data |= {"exit_code": event.exit_code}
    return json.dumps(data)


def _event_from_line(line: str) -> Event | None:
    """One parsed event, or None for a line that is not a known event."""
    try:
        data = json.loads(line)
        cls = _TYPES[data.pop("event")]
        data["at"] = datetime.fromisoformat(data["at"])
        return cls(**data)
    except (ValueError, KeyError, TypeError, AttributeError):
        return None


def _meta_to_json(meta: SessionMeta) -> str:
    launch = meta.launch
    binding = launch.binding
    data = {
        "schema": meta.schema,
        "id": meta.id,
        "project": meta.project,
        "task": meta.task,
        "name": meta.name,
        "created_at": format_time(meta.created_at),
        "launch": {
            "harness": launch.harness.value,
            "model": launch.model,
            "effort": launch.effort,
            "access": launch.access.value,
            "mode": launch.mode,
            "host": launch.host,
            "cwd": str(launch.cwd),
            "prompt": launch.prompt,
            "binding": None if binding is None else {
                "session_id": binding.session_id,
                "transcript": str(binding.transcript),
            },
        },
    }
    return json.dumps(data, indent=2) + "\n"


def _meta_from_json(data: dict[str, Any]) -> SessionMeta:
    launch = data["launch"]
    binding = launch["binding"]
    return SessionMeta(
        schema=data["schema"],
        id=SessionId(data["id"]),
        project=ProjectName(data["project"]),
        task=TaskName(data["task"]),
        name=SessionName(data["name"]),
        created_at=datetime.fromisoformat(data["created_at"]),
        launch=LaunchFacts(
            harness=HarnessName(launch["harness"]),
            model=launch["model"],
            effort=launch["effort"],
            access=Access(launch["access"]),
            mode=launch["mode"],
            host=launch["host"],
            cwd=Path(launch["cwd"]),
            prompt=launch["prompt"],
            binding=None if binding is None else HarnessBinding(
                session_id=binding["session_id"], transcript=Path(binding["transcript"])
            ),
        ),
    )
