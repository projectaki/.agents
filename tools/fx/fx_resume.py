import argparse
import fcntl
import os
from pathlib import Path
import re
import stat
import sys
from fx_access import validate_access


def session_metadata(session):
    path = Path(session) / "launch.txt"
    if path.is_symlink() or not path.is_file():
        raise ValueError("The session needs a regular launch.txt file.")
    metadata = dict(line.split("=", 1) for line in path.read_text().splitlines() if "=" in line)
    if metadata.get("reasoning") not in ("low", "medium", "high"):
        raise ValueError("The session has no valid saved reasoning level.")
    for field in ("agent", "model"):
        value = metadata.get(field, "")
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", value):
            raise ValueError(f"The session has no valid saved {field}.")
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


def exec_locked(session, command, access=None):
    descriptor = os.open(Path(session) / ".fx-agent.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise ValueError("The session lock must be a regular file.")
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(descriptor)
        raise ValueError("This session is already running. Exit it before resuming.")
    os.set_inheritable(descriptor, True)
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
