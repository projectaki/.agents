import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import sys
from fx_access import validate_access
from fx_models import session_model, validate_model


def session_metadata(session):
    path = Path(session) / "launch.txt"
    if path.is_symlink() or not path.is_file():
        raise ValueError("The session needs a regular launch.txt file.")
    metadata = dict(line.split("=", 1) for line in path.read_text().splitlines() if "=" in line)
    if metadata.get("reasoning") not in ("low", "medium", "high"):
        raise ValueError("The session has no valid saved reasoning level.")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", metadata.get("agent", "")):
        raise ValueError("The session has no valid saved agent.")
    if "model" not in metadata:
        metadata["model"] = session_model(session, "")
    validate_model(metadata["model"])
    return metadata


def resolve_session(task, agent, supplied):
    task = Path(task).resolve(strict=True)
    path = Path(supplied).absolute()
    context = task / "context"
    if not path.is_relative_to(context) or path == context:
        raise ValueError("Resume requires a session directory inside this task's context.")
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError("Resume paths must not contain symbolic links.")
        if parent == task:
            break
    path = path.resolve(strict=True)
    if not path.is_relative_to(context):
        raise ValueError("Resume requires a session directory inside this task's context.")
    for name in ("instructions.md", "input-context.md", "findings.md"):
        if (path / name).is_symlink() or not (path / name).is_file():
            raise ValueError(f"The session needs a regular {name} file.")
    if session_metadata(path)["agent"] != agent:
        raise ValueError("The selected session belongs to a different agent.")
    return path


def conversation_id(session, agent, *, allow_missing=False):
    session = Path(session)
    identities = set()
    events = session / "events"
    path = events / "callbacks.jsonl"
    if events.is_symlink() or path.is_symlink():
        raise ValueError("Conversation records must not be symbolic links.")
    if path.exists():
        if not path.is_file():
            raise ValueError("The callback log must be a regular file.")
        with path.open() as stream:
            for line in stream:
                if not line.endswith("\n"):
                    raise ValueError("The callback log has an incomplete last record. Preserve it before repairing capture.")
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if (not isinstance(record, dict) or record.get("agent") != agent
                        or record.get("source") != "hook"):
                    continue
                event = record.get("payload")
                if not isinstance(event, dict) or event.get("agent_id"):
                    continue
                identity = event.get("session_id")
                if isinstance(identity, str) and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", identity):
                    identities.add(identity)
    results = session / "results"
    if results.is_symlink():
        raise ValueError("Conversation results must not be symbolic links.")
    for directory in sorted(results.glob("turn-*")):
        path = directory / "metadata.json"
        if directory.is_symlink() or path.is_symlink():
            raise ValueError("Conversation metadata must not be symbolic links.")
        metadata = json.loads(path.read_text())
        if not isinstance(metadata, dict):
            raise ValueError(f"Expected conversation metadata in {path}.")
        identity = metadata.get("conversation_id")
        if (metadata.get("agent") == agent and isinstance(identity, str)
                and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", identity)):
            identities.add(identity)
    if not identities and allow_missing:
        return None
    if len(identities) != 1:
        raise ValueError(f"The session needs exactly one recorded {agent.title()} conversation identifier.")
    return identities.pop()


@contextmanager
def session_lock(session):
    descriptor = os.open(Path(session) / ".fx-agent.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError("The session lock must be a regular file.")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("This session is already running. Exit it before resuming.") from None
        os.set_inheritable(descriptor, True)
        yield
    finally:
        os.close(descriptor)


def exec_locked(session, command, access=None):
    with session_lock(session):
        if access is not None:
            path = Path(session) / "access.txt"
            if path.is_symlink():
                raise ValueError("Saved access must not be a symbolic link.")
            path.write_text(validate_access(access) + "\n")
        os.execvp(command[0], command)


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="action", required=True)
    resolve = commands.add_parser("resolve")
    resolve.add_argument("task")
    resolve.add_argument("agent")
    resolve.add_argument("session")
    metadata = commands.add_parser("metadata")
    metadata.add_argument("session")
    metadata.add_argument("field", choices=("agent", "reasoning", "model"))
    lock = commands.add_parser("lock")
    lock.add_argument("--access", choices=("auto", "full"))
    lock.add_argument("session")
    lock.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if args.action == "resolve":
            print(resolve_session(args.task, args.agent, args.session))
        elif args.action == "metadata":
            print(session_metadata(args.session)[args.field])
        else:
            if not args.command:
                raise ValueError("Supply an agent command to lock.")
            exec_locked(args.session, args.command, args.access)
    except (OSError, ValueError) as error:
        print(f"fx: Cannot resume or launch session: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
