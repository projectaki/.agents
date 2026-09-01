#!/usr/bin/env python3
"""Validate Factory telemetry and rebuild a compact analytical summary."""

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


START_TO_END = {
    "operation_started": {"operation_succeeded", "operation_failed", "operation_interrupted"},
    "recovery_started": {"recovery_finished"},
    "wait_started": {"wait_finished"},
    "external_action_attempted": {"external_action_succeeded", "external_action_failed"},
}
END_EVENTS = {event for events in START_TO_END.values() for event in events}
FAILURE_EVENTS = {"operation_failed", "external_action_failed"}
RUN_STARTS = {"run_started", "run_resumed"}
RUN_TERMINALS = {"run_finished", "run_interrupted"}
ACTOR_TERMINALS = {"actor_completed", "actor_interrupted", "actor_replaced"}


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
    resolver = Path(__file__).resolve().parents[2] / "factory-handoff" / "scripts" / "resolve-task-root.sh"
    result = subprocess.run([str(resolver)], check=True, capture_output=True, text=True)
    return Path(result.stdout.strip())


def load_events(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path.exists():
        return events, ["Telemetry file does not exist."]
    event_ids: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
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
    return str(event.get("run_id", "")), str(event.get("operation_id", "")), int(event.get("attempt", 1))


def actor_key(event: dict[str, Any]) -> str:
    return str(event.get("invocation_id") or event.get("assignment_id") or "")


def analyze(events: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(events, key=lambda event: (parse_time(str(event["occurred_at"])), str(event["event_id"])))
    defects: list[str] = []
    starts: dict[tuple[str, str, int], dict[str, Any]] = {}
    finished_spans: set[tuple[str, str, int]] = set()
    category_ms: Counter[str] = Counter()
    failures = sum(event["event_type"] in FAILURE_EVENTS for event in ordered)
    retries = 0
    operation_effort_ms = 0
    failed_attempts: set[tuple[str, str, int]] = set()

    run_events: dict[str, list[dict[str, Any]]] = defaultdict(list)
    actor_starts: Counter[str] = Counter()
    actor_terminals: Counter[str] = Counter()

    for event in ordered:
        event_type = str(event["event_type"])
        run_id = str(event.get("run_id") or "")
        if run_id:
            run_events[run_id].append(event)
        if event_type == "actor_dispatched" and actor_key(event):
            actor_starts[actor_key(event)] += 1
        if event_type in ACTOR_TERMINALS and actor_key(event):
            actor_terminals[actor_key(event)] += 1

        if event_type in START_TO_END and event.get("operation_id"):
            key = span_key(event)
            if key in starts or key in finished_spans:
                defects.append(f"Duplicate start for span {key}.")
            starts[key] = event
            attempt = key[2]
            if attempt > 1:
                retries += 1
                prior_key = (key[0], key[1], attempt - 1)
                if prior_key not in failed_attempts:
                    defects.append(f"Retry span {key} has no failed prior attempt.")
                if not event.get("retry_of") or not (event.get("retry_reason") or event.get("precondition_change")):
                    defects.append(f"Retry span {key} lacks correlation or justification.")
            if event_type == "recovery_started" and not any(
                failed[0] == key[0] for failed in failed_attempts
            ):
                defects.append(f"Recovery span {key} starts before a failure in its run.")
        elif event_type in END_EVENTS and event.get("operation_id"):
            key = span_key(event)
            if key in finished_spans:
                defects.append(f"Duplicate terminal event for span {key}.")
                continue
            start = starts.pop(key, None)
            if start is None:
                defects.append(f"Terminal event for span {key} has no start.")
                continue
            allowed = START_TO_END[str(start["event_type"])]
            if event_type not in allowed:
                defects.append(f"Span {key} ends with incompatible event {event_type}.")
                continue
            finished_spans.add(key)
            if event_type in {"operation_failed", "operation_interrupted", "external_action_failed"}:
                failed_attempts.add(key)
            duration_ms = int(event.get("duration_ms") or (
                parse_time(str(event["occurred_at"])) - parse_time(str(start["occurred_at"]))
            ).total_seconds() * 1000)
            if duration_ms < 0:
                defects.append(f"Span {key} has negative duration.")
                duration_ms = 0
            category = str(event.get("category") or start.get("category") or "other")
            category_ms[category] += duration_ms
            operation_effort_ms += duration_ms

    for key, count in actor_starts.items():
        if count != 1:
            defects.append(f"Actor {key} has {count} dispatch events.")
        if actor_terminals[key] != 1:
            defects.append(f"Actor {key} has {actor_terminals[key]} terminal events.")
    for key, count in actor_terminals.items():
        if count != 1 and actor_starts[key] == 0:
            defects.append(f"Actor {key} has {count} terminal events.")
        if actor_starts[key] != 1:
            defects.append(f"Actor {key} terminal event has no unique dispatch.")

    exact_active_ms = 0
    lower_bound_active_ms = 0
    incomplete_runs = 0
    intervals: list[tuple[datetime, datetime]] = []
    interrupted_runs = {str(event.get("run_id")) for event in ordered if event["event_type"] == "run_interrupted"}
    for run_id, run in run_events.items():
        run_starts = [event for event in run if event["event_type"] in RUN_STARTS]
        terminals = [event for event in run if event["event_type"] in RUN_TERMINALS]
        if len(run_starts) != 1:
            defects.append(f"Run {run_id} has {len(run_starts)} start events.")
            if not run_starts:
                continue
        if len(terminals) > 1:
            defects.append(f"Run {run_id} has {len(terminals)} terminal events.")
        start_time = parse_time(str(run_starts[0]["occurred_at"]))
        terminal = terminals[0] if terminals else run[-1]
        end_time = parse_time(str(terminal["occurred_at"]))
        duration = max(int((end_time - start_time).total_seconds() * 1000), 0)
        intervals.append((start_time, end_time))
        if terminal["event_type"] == "run_finished":
            exact_active_ms += duration
        else:
            lower_bound_active_ms += duration
            incomplete_runs += 1

    missing_results = list(starts.values())
    for start in missing_results:
        if str(start.get("run_id")) not in interrupted_runs:
            defects.append(f"Span {span_key(start)} has no terminal event.")

    intervals.sort()
    pause_ms = sum(
        max(int((current[0] - previous[1]).total_seconds() * 1000), 0)
        for previous, current in zip(intervals, intervals[1:])
    )
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
        "defects": defects,
    }


def render_summary(analysis: dict[str, Any], errors: list[str]) -> str:
    defects = [*errors, *analysis["defects"]]
    lines = [
        "# Factory telemetry summary",
        "",
        "This rebuildable analysis is not canonical task state.",
        "",
        "## Time",
        "",
        "| Measure | Value |",
        "| --- | --- |",
        f"| Calendar elapsed | {format_duration(analysis['calendar_ms'])} |",
        f"| Completed-run active time | {format_duration(analysis['exact_active_ms'])} |",
        f"| Incomplete-run lower bound | {format_duration(analysis['lower_bound_active_ms'])} |",
        f"| Pause or unobserved gap | {format_duration(analysis['pause_ms'])} |",
        f"| Categorized operation time | {format_duration(analysis['operation_effort_ms'])} |",
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
    lines.extend(f"- {defect}" for defect in defects) if defects else lines.append("None identified.")
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
        all_errors = [*errors, *analysis["defects"]]
        telemetry_root.mkdir(parents=True, exist_ok=True)
        (telemetry_root / "summary.md").write_text(render_summary(analysis, errors), encoding="utf-8")
        for error in all_errors:
            print(error, file=sys.stderr)
        return 1 if args.strict and all_errors else 0
    except Exception as error:
        print(f"Telemetry summary was not written: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
