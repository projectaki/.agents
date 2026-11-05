import argparse
import os
from pathlib import Path
import sys


def validate_access(value):
    if value not in ("auto", "full"):
        raise ValueError("Access must be auto or full.")
    return value


def saved_access(directory):
    path = Path(directory) / "access.txt"
    if path.is_symlink():
        raise ValueError("Saved access must not be a symbolic link.")
    if not path.exists():
        return None
    return validate_access(path.read_text().strip())


def resolve_access(explicit=None, directory=None):
    if explicit is not None:
        return validate_access(explicit)
    if directory is not None:
        saved = saved_access(directory)
        if saved is not None:
            return saved
    return validate_access(os.environ.get("FX_ACCESS", "auto"))


def session_access(session):
    return saved_access(session) or "auto"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("resolve", "read"))
    parser.add_argument("--access")
    parser.add_argument("--saved", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "read":
            if args.saved is None:
                raise ValueError("Supply a session directory with --saved.")
            print(session_access(args.saved))
        else:
            print(resolve_access(args.access, args.saved))
    except (OSError, ValueError) as error:
        print(f"fx: Cannot select agent access: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
