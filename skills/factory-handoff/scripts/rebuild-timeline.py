#!/usr/bin/env python3
"""Rebuild the canonical Factory timeline from checkpoints and routes."""

from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path
from typing import Any

from history_records import counts, load_records


def timestamp(value: object) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat().replace("+00:00", "Z")
    return str(value or "unknown")


def compact(value: object) -> str:
    return " ".join(str(value or "").split()).replace("|", "\\|")


def render(task_root: Path) -> str:
    checkpoints, routes, errors = load_records(task_root)
    if errors:
        raise ValueError("; ".join(errors))
    metrics = counts(checkpoints, routes)
    rows: list[tuple[str, str]] = []

    for path, manifest in checkpoints:
        lifecycle = compact(manifest.get("lifecycle"))
        outcome = manifest.get("verification_verdict") or manifest.get("review_verdict") or manifest.get("actor_outcome")
        rationale = manifest.get("selection_rationale") or "Canonical lifecycle result."
        relative = path.relative_to(task_root / "history")
        row = (
            f"| {timestamp(manifest.get('created_at'))} | checkpoint {int(manifest['checkpoint_sequence']):06d} "
            f"| Lifecycle result | {lifecycle} | {compact(outcome)} | {compact(rationale)} "
            f"| [manifest]({relative.as_posix()}) |"
        )
        rows.append((timestamp(manifest.get("created_at")), row))

    for path, decision, disposition in routes:
        selected = decision.get("selected") if isinstance(decision.get("selected"), dict) else {}
        movement = f"{decision.get('from')} to {selected.get('to')}"
        rationale = selected.get("rationale") or selected.get("edge") or "Route evaluated."
        relative = path.relative_to(task_root / "history")
        decision_row = (
            f"| {timestamp(decision.get('created_at'))} | route {int(decision['route_sequence']):06d} "
            f"| Route proposed | {compact(movement)} | {compact(selected.get('edge'))} | {compact(rationale)} "
            f"| [decision]({relative.as_posix()}) |"
        )
        rows.append((timestamp(decision.get("created_at")), decision_row))
        if disposition:
            disposition_path = path.parent / "disposition.md"
            disposition_relative = disposition_path.relative_to(task_root / "history")
            disposition_row = (
                f"| {timestamp(disposition.get('decided_at'))} | route {int(decision['route_sequence']):06d} "
                f"| Route {compact(disposition.get('status'))} | {compact(movement)} "
                f"| transition committed: {compact(disposition.get('transition_committed'))} "
                f"| {compact(disposition.get('rejection_reason') or disposition.get('approval_reference') or 'No additional rationale.')} "
                f"| [disposition]({disposition_relative.as_posix()}) |"
            )
            rows.append((timestamp(disposition.get("decided_at")), disposition_row))

    rows.sort(key=lambda item: (item[0], item[1]))
    return "\n".join([
        "# Timeline",
        "",
        "Rebuildable, noncanonical view of canonical Factory history.",
        "",
        f"Counts: checkpoints {metrics['checkpoints']} | routes {metrics['routes']} | rework loops {metrics['rework']} | rejected routes {metrics['rejected']}",
        "",
        "| Time (UTC) | ID | Event | Lifecycle or movement | Outcome or guard | Rationale | Record |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        *(row for _, row in rows),
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_root")
    args = parser.parse_args()
    task_root = Path(args.task_root)
    timeline_path = task_root / "history" / "timeline.md"
    timeline_path.parent.mkdir(parents=True, exist_ok=True)
    timeline_path.write_text(render(task_root), encoding="utf-8")
    print(f"Rebuilt Factory timeline: {timeline_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
