import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import sys


def inventory_task(task, session):
    task = Path(task).resolve(strict=True)
    session = Path(session).resolve(strict=True)
    if not session.is_relative_to(task / "context" / "analyses"):
        raise ValueError("Analysis sessions must be inside this task's context/analyses directory.")
    records = []

    def walk_error(error):
        records.append({"path": error.filename, "error": str(error)})

    for directory, children, files in os.walk(task, followlinks=False, onerror=walk_error):
        parent = Path(directory)
        for name in sorted(children + files):
            path = parent / name
            relative = path.relative_to(task).as_posix()
            if path.is_symlink():
                records.append({"path": relative, "excluded": "Symbolic link."})
        children[:] = sorted(name for name in children
                             if not (parent / name).is_symlink()
                             and (parent / name) not in (task / "repo", task / "context" / "analyses"))
        for name in sorted(files):
            path = parent / name
            if path.is_symlink():
                continue
            record = {"path": path.relative_to(task).as_posix()}
            try:
                descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                with os.fdopen(descriptor, "rb") as stream:
                    before = os.fstat(stream.fileno())
                    if not stat.S_ISREG(before.st_mode):
                        record["excluded"] = "Not a regular file."
                    else:
                        digest = hashlib.sha256()
                        size = 0
                        lines = 0
                        last = b""
                        remaining = before.st_size
                        while remaining:
                            chunk = stream.read(min(65536, remaining))
                            if not chunk:
                                break
                            remaining -= len(chunk)
                            digest.update(chunk)
                            size += len(chunk)
                            lines += chunk.count(b"\n")
                            last = chunk[-1:]
                        after = os.fstat(stream.fileno())
                        record.update(bytes=size, lines=lines + int(bool(last) and last != b"\n"),
                                      sha256=digest.hexdigest(), modified_ns=after.st_mtime_ns,
                                      changed_during_inventory=(before.st_size != after.st_size
                                                                or before.st_mtime_ns != after.st_mtime_ns))
            except OSError as error:
                record["error"] = str(error)
            records.append(record)
    return {
        "task": str(task), "observed_at": datetime.now(timezone.utc).isoformat(),
        "excluded": {"repo/": "Inspect relevant source and instructions separately; current source is not historical proof.",
                     "context/analyses/": "Analysis sessions are not original task evidence."},
        "files": sorted(records, key=lambda record: str(record["path"])),
        "limitations": "This is an inventory, not a copied archive. Files can change after inventory. Missing evidence does not prove an action did not occur.",
    }


def main():
    parser = argparse.ArgumentParser(description="Inventory task evidence for an fx retrospective.")
    parser.add_argument("task")
    parser.add_argument("session")
    args = parser.parse_args()
    try:
        print(json.dumps(inventory_task(args.task, args.session), indent=2))
    except (OSError, ValueError) as error:
        print(f"fx: Cannot inventory task evidence: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
