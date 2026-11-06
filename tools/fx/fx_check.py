import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

from fx_source import source_identity


def check_records(context):
    checks = context / "checks"
    if checks.is_symlink():
        raise ValueError(f"Check directory must not be a symbolic link: {checks}")
    records = []
    for path in checks.glob("*/result.json"):
        if path.is_symlink() or path.parent.is_symlink():
            raise ValueError(f"Check record must not be a symbolic link: {path}")
        records.append(json.loads(path.read_text(encoding="utf-8")))
    return sorted(records, key=lambda record: record["started_at"])


def freshness(record, current):
    identities = [
        (source.get("revision"), source.get("content_sha256"))
        for source in (record["source_before"], record["source_after"], current)
    ]
    if any(None in identity for identity in identities):
        return "source unavailable"
    if identities[0] != identities[1]:
        return "source changed during check"
    if identities[1] != identities[2]:
        return "historical"
    return "current"


class CheckProcess:
    def __init__(self):
        self.child = None
        self.interrupted = None
        self.kill_at = None

    def forward_signal(self, signum):
        if self.child is not None:
            try:
                os.killpg(self.child.pid, signum)
            except ProcessLookupError:
                pass

    def interrupt(self, signum, _frame):
        if self.interrupted is None:
            self.interrupted = signum
            self.kill_at = time.monotonic() + 5
        self.forward_signal(signum)

    def acquire(self, lock):
        while self.interrupted is None:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except BlockingIOError:
                time.sleep(0.1)

    def run(self, command, repo, env, output):
        if self.interrupted is not None:
            return None
        self.child = subprocess.Popen(
            command, cwd=repo, env=env, stdin=subprocess.DEVNULL,
            stdout=output, stderr=subprocess.STDOUT, start_new_session=True,
        )
        if self.interrupted is not None:
            self.forward_signal(self.interrupted)
        try:
            while True:
                try:
                    return self.child.wait(timeout=0.1)
                except subprocess.TimeoutExpired:
                    if self.kill_at is not None and time.monotonic() >= self.kill_at:
                        self.forward_signal(signal.SIGKILL)
        finally:
            if self.interrupted is not None:
                self.forward_signal(signal.SIGKILL)
            self.child = None


def run_check(task, session, command, *, shared_lock=None, tmp_dir=None):
    context = task / "context"
    checks = context / "checks"
    if context.is_symlink() or checks.is_symlink():
        raise ValueError("Check evidence directories must not be symbolic links.")
    checks.mkdir(mode=0o700, exist_ok=True)
    run = checks / uuid4().hex
    run.mkdir(mode=0o700)
    output_path = run / "output.log"
    print(f"fx: Check output: {output_path}", file=sys.stderr, flush=True)
    process = CheckProcess()
    repo = task / "repo"
    record = {
        "schema_version": 1,
        "session": session,
        "command": command,
        "evidence": str(output_path.relative_to(task)),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "lock_wait_seconds": 0,
        "execution_seconds": None,
        "error": None,
    }
    returncode = None
    env = os.environ.copy()
    with ExitStack() as cleanup, output_path.open("xb") as output:
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            previous = signal.signal(signum, process.interrupt)
            cleanup.callback(signal.signal, signum, previous)
        try:
            with ExitStack() as resources:
                if tmp_dir is not None:
                    env["TMPDIR"] = resources.enter_context(
                        tempfile.TemporaryDirectory(prefix="fx-check-", dir=tmp_dir))
                if shared_lock is not None:
                    shared_lock.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                    lock = resources.enter_context(shared_lock.open("a"))
                    waiting = time.monotonic()
                    process.acquire(lock)
                    record["lock_wait_seconds"] = time.monotonic() - waiting
                record["source_before"] = source_identity(repo)
                if process.interrupted is None:
                    started = time.monotonic()
                    try:
                        returncode = process.run(command, repo, env, output)
                    finally:
                        record["execution_seconds"] = time.monotonic() - started
                record["source_after"] = source_identity(repo)
        except OSError as error:
            record["error"] = str(error)
            print(f"fx: Check error: {error}", file=sys.stderr)
        record.setdefault("source_before", {})
        if "source_after" not in record:
            record["source_after"] = source_identity(repo)
        record["exit_code"] = returncode if returncode is not None and returncode >= 0 else None
        record["termination_signal"] = -returncode if returncode is not None and returncode < 0 else None
        record["interruption_signal"] = process.interrupted
        if process.interrupted is not None or record["termination_signal"] is not None:
            record["result"] = "interrupted"
        elif record["error"] is not None:
            record["result"] = "error"
        else:
            record["result"] = "passed" if returncode == 0 else "failed"
        pending = run / ".result.json"
        pending.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        pending.replace(run / "result.json")
    print(f"fx: Check {record['result']}: {run / 'result.json'}", file=sys.stderr)
    return returncode, process.interrupted


def main():
    parser = argparse.ArgumentParser(
        usage="fx task check [--session DIR] [--heavy] [--tmp-dir DIR] -- COMMAND [ARG ...]\n"
              "       fx task check status",
        description="Run a check once from the task repository and record its outcome.")
    parser.add_argument("--task", type=Path, required=True, help=argparse.SUPPRESS)
    parser.add_argument("--session", type=Path, help="Factory session to associate with the check")
    parser.add_argument("--heavy", action="store_true", help="Use the shared lock for this user on this host")
    parser.add_argument("--tmp-dir", type=Path, help="Parent for a private temporary directory")
    options, command = sys.argv[1:], []
    separator = "--" in options
    if separator:
        split = options.index("--")
        options, command = options[:split], options[split + 1:]
    parser.add_argument("action", nargs="?", choices=["status"])
    args = parser.parse_args(options)
    try:
        context = args.task / "context"
        if not context.is_dir() or context.is_symlink():
            raise ValueError(f"Expected a task context directory: {context}")
        if args.action == "status" and not (separator or args.session or args.heavy or args.tmp_dir):
            current = source_identity(args.task / "repo")
            records = check_records(context)
            if not records:
                print("No recorded checks.")
            for record in records:
                owner = record["session"] or "manual"
                print(f"{record['result']} ({freshness(record, current)}) [{owner}] "
                      f"{json.dumps(record['command'])} — {args.task / record['evidence']}")
            return 0
        if args.action or not command:
            parser.error("Supply a command after --, or use status.")
        session_path = args.session or os.environ.get("FX_SESSION_CONTEXT_DIR")
        session = None
        if session_path:
            path = Path(session_path).resolve(strict=True)
            if not path.is_relative_to(context) or not (path / "instructions.md").is_file():
                raise ValueError(f"Expected a Factory session directory in this task: {path}")
            session = str(path.relative_to(context))
        lock = Path.home() / ".cache/fx/heavy-check.lock" if args.heavy else None
        tmp_dir = args.tmp_dir.resolve(strict=True) if args.tmp_dir else None
        if tmp_dir is not None and tmp_dir.is_relative_to(args.task / "repo"):
            raise ValueError("The temporary directory must be outside the repository.")
        code, interruption = run_check(args.task, session, command, shared_lock=lock, tmp_dir=tmp_dir)
    except (OSError, ValueError) as error:
        print(f"fx: {error}", file=sys.stderr)
        return 1
    signum = interruption or (-code if code is not None and code < 0 else None)
    if signum is not None:
        if signum not in (signal.SIGKILL, signal.SIGSTOP):
            signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)
        return 128 + signum
    return code if code is not None else 1


if __name__ == "__main__":
    sys.exit(main())
