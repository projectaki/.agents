from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile


TOKEN_FIELDS = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens",
                "output_tokens", "reasoning_output_tokens")


def validate_usage(value):
    if not isinstance(value, dict):
        raise ValueError("Usage must be an object.")
    for field in TOKEN_FIELDS:
        count = value.get(field)
        if count is not None and (type(count) is not int or count < 0):
            raise ValueError(f"Invalid usage count: {field}.")
    cost = value.get("cost_usd")
    if cost is not None and (type(cost) not in (int, float) or not math.isfinite(cost) or cost < 0):
        raise ValueError("Invalid usage cost.")
    if value.get("cost_kind") not in ("reported", "estimated", "unavailable"):
        raise ValueError("Invalid usage cost kind.")
    if (cost is None) != (value["cost_kind"] == "unavailable"):
        raise ValueError("Usage cost and cost kind disagree.")
    if value.get("coverage") not in ("complete", "partial", "unavailable"):
        raise ValueError("Invalid usage coverage.")
    if value["coverage"] == "complete" and any(value.get(field) is None for field in ("input_tokens", "output_tokens")):
        raise ValueError("Complete usage requires input and output counts.")
    if not isinstance(value.get("notes"), list) or not all(isinstance(note, str) for note in value["notes"]):
        raise ValueError("Usage notes must be strings.")
    for field in ("cached_input_tokens", "cache_write_input_tokens"):
        if value.get(field) is not None and value.get("input_tokens") is not None and value[field] > value["input_tokens"]:
            raise ValueError("Cached input exceeds total input.")
    if all(value.get(field) is not None for field in ("input_tokens", "cached_input_tokens", "cache_write_input_tokens")):
        if value["cached_input_tokens"] + value["cache_write_input_tokens"] > value["input_tokens"]:
            raise ValueError("Cache reads and writes exceed total input.")
    if value.get("reasoning_output_tokens") is not None and value.get("output_tokens") is not None:
        if value["reasoning_output_tokens"] > value["output_tokens"]:
            raise ValueError("Reasoning output exceeds total output.")
    return value


def unavailable_usage(reason):
    return {**dict.fromkeys(TOKEN_FIELDS), "cost_usd": None, "cost_kind": "unavailable",
            "coverage": "unavailable", "notes": [reason]}


def collect_usage(tool_dir, session, agent):
    adapter = tool_dir / "agents" / f"{agent}.usage"
    if not os.access(adapter, os.X_OK):
        return unavailable_usage("No usage adapter is installed.")
    try:
        result = subprocess.run([str(adapter), str(session)], stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=10)
        if result.returncode:
            return unavailable_usage(f"Usage adapter exited with status {result.returncode}.")
        return validate_usage(json.loads(result.stdout))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return unavailable_usage(f"Usage collection failed: {type(error).__name__}.")


def write_json(path, value):
    atomic_write(path, json.dumps(value, indent=2, allow_nan=False) + "\n")


def atomic_write(path, content):
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        pending = Path(stream.name)
        try:
            stream.write(content)
            stream.close()
            pending.replace(path)
        finally:
            pending.unlink(missing_ok=True)


def group_usage(group, manifest, state):
    active = {member["session"] for member in manifest["members"]}
    attempts = []
    for name, outcome in state["members"].items():
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", name) or name in (".", ".."):
            raise ValueError("Invalid usage session path.")
        session = group / name
        if session.is_symlink():
            raise ValueError("Usage session must not be a symbolic link.")
        usage = unavailable_usage("No usage record was saved for this attempt.")
        metadata = {}
        try:
            launch = session / "launch.txt"
            record = session / "usage.json"
            if launch.is_symlink() or record.is_symlink():
                raise ValueError("Usage inputs must not be symbolic links.")
            metadata = dict(line.split("=", 1) for line in launch.read_text().splitlines())
            model = session / "model.txt"
            if "model" not in metadata and model.is_file() and not model.is_symlink():
                metadata["model"] = model.read_text().strip()
            if record.exists():
                usage = validate_usage(json.loads(record.read_text()))
        except (OSError, ValueError) as error:
            usage = unavailable_usage(f"Cannot read usage record: {type(error).__name__}.")
        attempts.append({"session": name, "active": name in active,
                         "agent": metadata.get("agent", "unknown"),
                         "model": metadata.get("model", "unknown"),
                         "reasoning": metadata.get("reasoning", "unknown"),
                         "status": outcome["status"],
                         "started_at": outcome.get("started_at"),
                         "finished_at": outcome.get("finished_at"),
                         "runtime_seconds": outcome.get("runtime_seconds"),
                         "usage": usage})
    return {"schema_version": 1, "recorded_at": datetime.now(timezone.utc).isoformat(),
            "scope": "Group member attempts, including failures and retries; excludes synthesis.",
            "wall_seconds": state.get("wall_seconds"), "attempts": attempts}


def render_group_usage(report):
    lines = ["# Group usage", "", report["scope"], "",
             "Input includes cached input and cache writes. Output includes reasoning when reported.",
             "Unknown values are unavailable, not zero. Partial usage is a lower bound.",
             "Costs marked estimated are not invoices. Subscription charges are not inferred.", "",
             "| Session | Agent / model | Reasoning | Status | Runtime | Input | Cached | Cache write | Output | Reasoning output | Cost USD | Coverage |",
             "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for attempt in report["attempts"]:
        usage = attempt["usage"]
        duration = attempt["runtime_seconds"]
        runtime = "unavailable" if duration is None else f"{duration:.2f}s"
        cost = "unavailable" if usage.get("cost_usd") is None else f"${usage['cost_usd']:.6f} ({usage['cost_kind']})"
        counts = ["unavailable" if usage.get(key) is None else f"{usage[key]:,}" for key in TOKEN_FIELDS]
        cells = [attempt["session"], f"{attempt['agent']} / {attempt['model']}", attempt["reasoning"],
                 attempt["status"], runtime, *counts, cost, usage["coverage"]]
        lines.append("| " + " | ".join(str(cell).replace("|", "\\|").replace("\n", " ") for cell in cells) + " |")
    lines.append("")
    if report["wall_seconds"] is not None:
        lines.append(f"Group execution time across runs: {report['wall_seconds']:.2f}s. Excludes time waiting to retry and synthesis.")
    for attempt in report["attempts"]:
        for note in attempt["usage"]["notes"]:
            lines.append(f"- {attempt['session']}: {note}")
    return "\n".join(lines) + "\n"


def save_group_usage(group, manifest, state):
    report = group_usage(group, manifest, state)
    summary = render_group_usage(report)
    write_json(group / "usage-summary.json", report)
    atomic_write(group / "usage-summary.md", summary)
    print(summary, flush=True)
    print(f"fx: Usage summary saved: {group / 'usage-summary.md'}", flush=True)
