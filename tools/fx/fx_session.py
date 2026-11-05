import argparse
import fcntl
import os
from pathlib import Path
import re
import sys


def create_session_directory(task, parent, name):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", name):
        raise ValueError("Session names must contain only letters, digits, underscores, dots, or hyphens.")
    task = Path(task).resolve(strict=True)
    parent = Path(parent).resolve(strict=True)
    if not parent.is_relative_to(task / "context"):
        raise ValueError("Session directories must be inside the task context.")
    descriptor = os.open(task / ".fx-session-sequence", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "r+", encoding="utf-8") as sequence:
        fcntl.flock(sequence, fcntl.LOCK_EX)
        saved = sequence.read()
        if saved and not re.fullmatch(r"[0-9]+\n?", saved):
            raise ValueError("Invalid task session sequence. Preserve existing context and inspect .fx-session-sequence.")
        number = int(saved or "0")
        while True:
            number += 1
            sequence.seek(0)
            sequence.write(f"{number}\n")
            sequence.truncate()
            sequence.flush()
            os.fsync(sequence.fileno())
            destination = parent / f"{number:06d}-{name}"
            try:
                destination.mkdir(mode=0o700)
            except FileExistsError:
                continue
            return destination


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("task")
    parser.add_argument("parent")
    parser.add_argument("name")
    args = parser.parse_args()
    try:
        print(create_session_directory(args.task, args.parent, args.name))
    except (OSError, ValueError) as error:
        print(f"fx: Cannot create session context: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
