#!/usr/bin/env python3
"""Validate Factory telemetry JSONL and rebuild its analytical summary."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from telemetry_schema import EVENT_TYPES


START_EVENTS = {
    "operation_started", "recovery_started", "wait_started",
    "external_action_attempted",
}
END_EVENTS = {
    "operation_succeeded", "operation_failed", "operation_interrupted",
    "recovery_finished", "wait_finished", "external_action_succeeded",
    "external_action_failed",
}
FAILURE_EVENTS = {"operation_failed", "external_action_failed"}


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def format_duration(milliseconds: int) -> str:
    seconds = milliseconds // 1000
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def resolve_task_root(explicit_root: str | None) -> Path:
    if explicit_root:
        return Path(explicit_root).expanduser().resolve()
    resolver = Path(__file__).resolve().parents[2] / "factory-handoff" / "scripts" / "resolve-handoff-path.sh"
    result = subprocess.run([str(resolver), "--root"], check=True, capture_output=True, text=True)
    return Path(result.stdout.strip())


def load_events(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path.exists():
        return events, ["Telemetry file does not exist."]

    lines = path.read_text(encoding="utf-8").splitlines()
    event_ids: set[str] = set()
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            errors.append(f"Line {line_number} is empty.")
            continue
        try:
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError("event is not an object")
            for field in ("schema_version", "event_id", "event_type", "occurred_at", "recorded_at", "summary"):
                if field not in event:
                    raise ValueError(f"missing {field}")
            if event["schema_version"] != 1:
                raise ValueError("unsupported schema_version")
            if event["event_type"] not in EVENT_TYPES:
                raise ValueError(f"unknown event_type {event['event_type']!r}")
            if event["event_id"] in event_ids:
                raise ValueError(f"duplicate event_id {event['event_id']!r}")
            parse_time(str(event["occurred_at"]))
            parse_time(str(event["recorded_at"]))
            event_ids.add(str(event["event_id"]))
            events.append(event)
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            errors.append(f"Line {line_number}: {error}")
    return events, errors


def span_key(event: dict[str, Any]) -> tuple[str, str, int]:
    return (
        str(event.get("run_id", "")),
        str(event.get("operation_id", "")),
        int(event.get("attempt", 1)),
    )


def analyze(events: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(events, key=lambda event: (parse_time(str(event["occurred_at"])), str(event["event_id"])))
    starts: dict[tuple[str, str, int], dict[str, Any]] = {}
    category_ms: Counter[str] = Counter()
    missing_results: list[dict[str, Any]] = []
    failures = 0
    retries = 0
    operation_effort_ms = 0

    for event in ordered:
        event_type = str(event["event_type"])
        if event_type in START_EVENTS and event.get("operation_id"):
            starts[span_key(event)] = event
            if int(event.get("attempt", 1)) > 1 or event.get("retry_of"):
                retries += 1
        elif event_type in END_EVENTS and event.get("operation_id"):
            start = starts.pop(span_key(event), None)
            if "duration_ms" in event:
                duration_ms = int(event["duration_ms"])
            elif start:
                duration_ms = int((parse_time(str(event["occurred_at"])) - parse_time(str(start["occurred_at"]))).total_seconds() * 1000)
            else:
                duration_ms = 0
            category = str(event.get("category") or (start or {}).get("category") or "other")
            category_ms[category] += max(duration_ms, 0)
            operation_effort_ms += max(duration_ms, 0)
        if event_type in FAILURE_EVENTS:
            failures += 1

    missing_results.extend(starts.values())

    run_events: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in ordered:
        if event.get("run_id"):
            run_events[str(event["run_id"])].append(event)

    exact_active_ms = 0
    lower_bound_active_ms = 0
    incomplete_runs = 0
    run_intervals: list[tuple[datetime, datetime, bool]] = []
    for run in run_events.values():
        starts_for_run = [event for event in run if event["event_type"] in {"run_started", "run_resumed"}]
        if not starts_for_run:
            continue
        start_time = parse_time(str(starts_for_run[0]["occurred_at"]))
        finishes = [event for event in run if event["event_type"] == "run_finished"]
        end_event = finishes[-1] if finishes else run[-1]
        end_time = parse_time(str(end_event["occurred_at"]))
        duration = max(int((end_time - start_time).total_seconds() * 1000), 0)
        exact = bool(finishes)
        run_intervals.append((start_time, end_time, exact))
        if exact:
            exact_active_ms += duration
        else:
            lower_bound_active_ms += duration
            incomplete_runs += 1

    run_intervals.sort()
    pause_ms = 0
    for previous, current in zip(run_intervals, run_intervals[1:]):
        pause_ms += max(int((current[0] - previous[1]).total_seconds() * 1000), 0)

    calendar_ms = 0
    if ordered:
        calendar_ms = max(int((parse_time(str(ordered[-1]["occurred_at"])) - parse_time(str(ordered[0]["occurred_at"]))).total_seconds() * 1000), 0)

    return {
        "event_count": len(events),
        "calendar_ms": calendar_ms,
        "exact_active_ms": exact_active_ms,
        "lower_bound_active_ms": lower_bound_active_ms,
        "pause_ms": pause_ms,
        "incomplete_runs": incomplete_runs,
        "failures": failures,
        "retries": retries,
        "operation_effort_ms": operation_effort_ms,
        "missing_results": missing_results,
        "category_ms": category_ms,
    }


def render_summary(analysis: dict[str, Any], errors: list[str]) -> str:
    lines = [
        "# Factory telemetry summary",
        "",
        "This file is a rebuildable, noncanonical analysis of `events.jsonl`.",
        "",
        "## Time",
        "",
        "| Measure | Value |",
        "| --- | --- |",
        f"| Calendar elapsed | {format_duration(analysis['calendar_ms'])} |",
        f"| Completed-run active time | {format_duration(analysis['exact_active_ms'])} |",
        f"| Incomplete-run lower bound | {format_duration(analysis['lower_bound_active_ms'])} |",
        f"| Pause or unobserved gap | {format_duration(analysis['pause_ms'])} |",
        f"| Summed operation effort | {format_duration(analysis['operation_effort_ms'])} |",
        "",
        "## Activity",
        "",
        f"- Events: {analysis['event_count']}",
        f"- Failed operations: {analysis['failures']}",
        f"- Retries: {analysis['retries']}",
        f"- Incomplete runs: {analysis['incomplete_runs']}",
        f"- Operations without a result: {len(analysis['missing_results'])}",
    ]
    if analysis["category_ms"]:
        lines.extend(["", "## Time by category", "", "| Category | Time |", "| --- | --- |"]) 
        for category, duration in sorted(analysis["category_ms"].items()):
            lines.append(f"| {category} | {format_duration(duration)} |")
    lines.extend(["", "## Telemetry defects", ""])
    if errors:
        lines.extend(f"- {error}" for error in errors)
    else:
        lines.append("None identified.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-root")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    try:
        task_root = resolve_task_root(args.task_root)
        telemetry_root = task_root / "telemetry"
        events, errors = load_events(telemetry_root / "events.jsonl")
        analysis = analyze(events)
        telemetry_root.mkdir(parents=True, exist_ok=True)
        summary_path = telemetry_root / "summary.md"
        summary_path.write_text(render_summary(analysis, errors), encoding="utf-8")
        print(f"Wrote telemetry summary to {summary_path}")
        for error in errors:
            print(error, file=sys.stderr)
        return 1 if args.strict and errors else 0
    except Exception as error:
        print(f"Telemetry summary was not written: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
