"""Shared Factory telemetry schema values and sanitization."""

from __future__ import annotations

import re
from datetime import datetime, timezone


EVENT_TYPES = {
    "run_started", "run_finished", "run_interrupted", "run_resumed",
    "actor_dispatched", "actor_completed", "actor_interrupted", "actor_replaced",
    "operation_started", "operation_succeeded", "operation_failed",
    "operation_interrupted", "recovery_started", "recovery_finished",
    "wait_started", "wait_finished", "external_action_attempted",
    "external_action_succeeded", "external_action_failed",
    "external_action_verified", "human_input_received", "human_decision_recorded",
    "workspace_changed", "artifact_changed", "artifact_invalidated",
    "event_corrected",
}
CATEGORIES = {
    "orchestration", "implementation", "verification", "review", "delivery",
    "environment_setup", "recovery", "human_wait", "external_wait",
    "external_action", "research", "other",
}
FAILURE_CLASSES = {
    "tool", "environment", "product", "network", "permission", "dependency",
    "timeout", "interruption", "unknown",
}
SECRET_PATTERNS = (
    re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(
        r"(?i)\b(password|passwd|token|api[_-]?key|secret|authorization)"
        r"\s*[:=]\s*[^\s,;]+"
    ),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def normalize_timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a UTC offset")
    return parsed.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sanitize(value: str) -> str:
    sanitized = value
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub(lambda match: f"{match.group(1)}=[REDACTED]", sanitized)
    return sanitized
