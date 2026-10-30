import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import stat
import sys
import time


def prepare_events(session):
    events = Path(session).resolve(strict=True) / "events"
    if events.is_symlink():
        raise ValueError("The events directory must not be a symbolic link.")
    events.mkdir(mode=0o700, exist_ok=True)
    return events


def save_event(session, agent, source, raw_payload):
    if not all(isinstance(value, str) and value for value in (agent, source)):
        raise ValueError("Event agent and source must be nonempty strings.")
    if not isinstance(raw_payload, str):
        raise ValueError("The event payload must be text.")
    record = {
        "schema_version": 1,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "monotonic_ns": time.monotonic_ns(),
        "agent": agent,
        "source": source,
    }
    try:
        record["payload"] = json.loads(raw_payload)
    except ValueError:
        record["raw_payload"] = raw_payload
    path = prepare_events(session) / "callbacks.jsonl"
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError("The callback log must be a regular file.")
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        offset = os.lseek(descriptor, 0, os.SEEK_END)
        if offset:
            os.lseek(descriptor, -1, os.SEEK_END)
            if os.read(descriptor, 1) != b"\n":
                raise ValueError("The callback log has an incomplete last record. Preserve it for analysis before repairing it.")
        record["offset"] = offset
        data = (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")
        try:
            remaining = memoryview(data)
            while remaining:
                written = os.write(descriptor, remaining)
                if not written:
                    raise OSError("The callback log write made no progress.")
                remaining = remaining[written:]
            os.fsync(descriptor)
        except OSError:
            os.ftruncate(descriptor, offset)
            raise
        return offset
    finally:
        os.close(descriptor)


def capture_event(session, agent, source, raw_payload):
    try:
        save_event(session, agent, source, raw_payload)
    except (OSError, ValueError) as error:
        message = f"fx: Diagnostic event capture failed: {error}\n"
        print(message, file=sys.stderr, end="")
        try:
            path = prepare_events(session) / "capture-error.txt"
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(message)
        except (OSError, ValueError):
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session")
    parser.add_argument("native_log")
    args = parser.parse_args()
    try:
        if Path(args.native_log).name != args.native_log or args.native_log in ("", ".", ".."):
            raise ValueError("Supply a native log filename, not a path.")
        events = prepare_events(args.session)
        descriptor = os.open(events / args.native_log, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(descriptor)
        print(events)
    except (OSError, ValueError) as error:
        print(f"fx: Cannot prepare diagnostic capture: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
