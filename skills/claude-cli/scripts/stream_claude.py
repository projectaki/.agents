#!/usr/bin/env python3
"""Run one Claude task and emit sanitized observable JSON-line events."""

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


def safe_context(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    context: dict[str, str] = {}
    for key in ("file_path", "path"):
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate:
            context[key] = candidate[:500]
    return context


def text_from_content(content: Any) -> str:
    if not isinstance(content, list):
        return ""
    return "".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )


class EventParser:
    def __init__(self) -> None:
        self.saw_text_delta = False
        self.final_result = ""
        self.error = ""

    def parse(self, event: dict[str, Any]) -> None:
        event_type = event.get("type")
        if event_type == "system" and event.get("subtype") == "init":
            emit("status", message="Claude initialized")
            return

        if event_type == "stream_event":
            inner = event.get("event")
            if not isinstance(inner, dict):
                return
            inner_type = inner.get("type")
            if inner_type == "content_block_start":
                block = inner.get("content_block")
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    emit("tool", name=str(block.get("name", "unknown")), context=safe_context(block.get("input")))
            elif inner_type == "content_block_delta":
                delta = inner.get("delta")
                if isinstance(delta, dict) and delta.get("type") == "text_delta":
                    text = delta.get("text")
                    if isinstance(text, str) and text:
                        self.saw_text_delta = True
                        emit("text", text=text)
            return

        if event_type == "assistant":
            message = event.get("message")
            if not isinstance(message, dict):
                return
            if not self.saw_text_delta:
                text = text_from_content(message.get("content"))
                if text:
                    emit("text", text=text)
            for block in message.get("content", []):
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    emit("tool", name=str(block.get("name", "unknown")), context=safe_context(block.get("input")))
            return

        if event_type == "result":
            result = event.get("result")
            if isinstance(result, str):
                self.final_result = result
            if event.get("subtype") not in (None, "success") or event.get("is_error"):
                self.error = "Claude reported an error"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--effort", choices=("low", "medium", "high", "xhigh", "max"), required=True)
    parser.add_argument("--permission-mode", required=True)
    parser.add_argument("--tools", required=True)
    parser.add_argument("--stall-seconds", type=int, default=300)
    parser.add_argument("--heartbeat-seconds", type=int, default=30)
    parser.add_argument("--claude-bin", default="claude", help=argparse.SUPPRESS)
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
        args.claude_bin,
        "-p",
        "--model", args.model,
        "--effort", args.effort,
        "--permission-mode", args.permission_mode,
        "--tools", args.tools,
        "--strict-mcp-config",
        "--no-chrome",
        "--no-session-persistence",
        "--output-format", "stream-json",
        "--include-partial-messages",
        "--verbose",
    ]

    emit("status", message="Starting Claude", model=args.model)
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
        emit("error", message=f"Unable to start Claude: {exc.strerror or type(exc).__name__}")
        return 2

    assert process.stdin and process.stdout and process.stderr
    process.stdin.write(prompt)
    process.stdin.close()

    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    parser = EventParser()
    last_event = time.monotonic()
    last_heartbeat = last_event
    diagnostics: list[str] = []

    try:
        while selector.get_map():
            now = time.monotonic()
            if process.poll() is None and now - last_event >= args.stall_seconds:
                terminate(process)
                emit("error", message=f"Claude stalled: no stream event for {args.stall_seconds} seconds")
                return 124

            if process.poll() is None and now - last_heartbeat >= args.heartbeat_seconds:
                emit("status", message="Claude is still working", idle_seconds=int(now - last_event))
                last_heartbeat = now

            for key, _ in selector.select(timeout=1):
                line = key.fileobj.readline()
                if not line:
                    selector.unregister(key.fileobj)
                    continue
                if key.data == "stderr":
                    if len(diagnostics) < 20:
                        diagnostics.append(line.strip()[:500])
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
        message = parser.error or f"Claude exited with code {exit_code}"
        emit("error", message=message)
        return exit_code or 1
    if not parser.final_result.strip():
        emit("error", message="Claude completed without a final response")
        return 1

    emit("result", status="completed", response=parser.final_result)
    emit("status", message="Claude completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
