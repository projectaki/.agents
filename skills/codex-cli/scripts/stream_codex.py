#!/usr/bin/env python3
"""Run one Codex task and emit sanitized observable JSON-line events."""

from __future__ import annotations

import argparse
import json
import os
import selectors
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def emit(kind: str, **payload: Any) -> None:
    print(json.dumps({"type": kind, **payload}, ensure_ascii=False), flush=True)


class EventParser:
    def __init__(self, delivery: str) -> None:
        self.observable = delivery == "observable"
        self.final_result = ""
        self.error = ""

    def emit_progress(self, kind: str, **payload: Any) -> None:
        if self.observable:
            emit(kind, **payload)

    def parse(self, event: dict[str, Any]) -> None:
        event_type = event.get("type")
        if event_type == "thread.started":
            self.emit_progress("status", message="Codex initialized")
            return
        if event_type == "turn.started":
            self.emit_progress("status", message="Codex is working")
            return
        if event_type in ("item.started", "item.completed"):
            self._parse_item(event_type, event.get("item"))
            return
        if event_type == "turn.completed":
            self.emit_progress("status", message="Codex turn completed")
            return
        if event_type in ("turn.failed", "error"):
            self.error = "Codex reported an error"

    def _parse_item(self, event_type: str, item: Any) -> None:
        if not isinstance(item, dict):
            return
        item_type = item.get("type")
        if item_type == "agent_message" and event_type == "item.completed":
            text = item.get("text")
            if isinstance(text, str) and text:
                self.final_result = text
                self.emit_progress("text", text=text)
            return
        if item_type == "reasoning":
            return
        if isinstance(item_type, str) and item_type:
            phase = "started" if event_type == "item.started" else "completed"
            self.emit_progress("tool", name=item_type, phase=phase)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--reasoning-effort", choices=("low", "medium", "high", "xhigh"), required=True)
    parser.add_argument("--sandbox", choices=("read-only", "workspace-write", "danger-full-access"), required=True)
    parser.add_argument("--delivery", choices=("observable", "result-only"), default="observable")
    parser.add_argument("--stall-seconds", type=int, default=300)
    parser.add_argument("--heartbeat-seconds", type=int, default=30)
    parser.add_argument("--codex-bin", default="codex", help=argparse.SUPPRESS)
    return parser.parse_args()


def terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> int:
    args = parse_args()
    repository = args.repository.expanduser().resolve()
    if not repository.is_dir() or not os.access(repository, os.R_OK):
        emit("error", message="Repository is not readable")
        return 2

    prompt = sys.stdin.read()
    if not prompt.strip():
        emit("error", message="Prompt is empty")
        return 2

    command = [
        args.codex_bin,
        "exec",
        "--ephemeral",
        "--sandbox", args.sandbox,
        "--color", "never",
        "--json",
        "-C", str(repository),
        "-m", args.model,
        "-c", f'model_reasoning_effort="{args.reasoning_effort}"',
        "-",
    ]

    if args.delivery == "observable":
        emit("status", message="Starting Codex", model=args.model)
    try:
        process = subprocess.Popen(
            command,
            cwd=repository,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except OSError as exc:
        emit("error", message=f"Unable to start Codex: {exc.strerror or type(exc).__name__}")
        return 2

    assert process.stdin and process.stdout and process.stderr
    process.stdin.write(prompt)
    process.stdin.close()

    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    parser = EventParser(args.delivery)
    last_event = time.monotonic()
    last_heartbeat = last_event

    try:
        while selector.get_map():
            now = time.monotonic()
            if process.poll() is None and now - last_event >= args.stall_seconds:
                terminate(process)
                emit("error", message=f"Codex stalled: no stream event for {args.stall_seconds} seconds")
                return 124
            if process.poll() is None and now - last_heartbeat >= args.heartbeat_seconds:
                if args.delivery == "observable":
                    emit("status", message="Codex is still working", idle_seconds=int(now - last_event))
                last_heartbeat = now

            for key, _ in selector.select(timeout=1):
                line = key.fileobj.readline()
                if not line:
                    selector.unregister(key.fileobj)
                    continue
                if key.data == "stderr":
                    continue
                last_event = time.monotonic()
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, dict):
                    parser.parse(event)
    finally:
        selector.close()
        if process.poll() is None:
            terminate(process)

    exit_code = process.wait()
    if exit_code != 0 or parser.error:
        emit("error", message=parser.error or f"Codex exited with code {exit_code}")
        return exit_code or 1
    if not parser.final_result.strip():
        emit("error", message="Codex completed without a final response")
        return 1

    emit("result", status="completed", response=parser.final_result)
    if args.delivery == "observable":
        emit("status", message="Codex completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
