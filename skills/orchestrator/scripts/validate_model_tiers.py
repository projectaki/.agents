#!/usr/bin/env python3
"""Validate the orchestrator's three-tier model policy."""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
EXPECTED = {
    "fast": {
        "codex_worker": "fast-worker",
        "codex_model": "gpt-5.6-luna",
        "codex_effort": "low",
        "claude_worker": "fast-worker",
        "claude_model": "claude-sonnet-5",
        "claude_effort": "low",
    },
    "standard": {
        "codex_worker": "standard-worker",
        "codex_model": "gpt-5.6-terra",
        "codex_effort": "medium",
        "claude_worker": "standard-worker",
        "claude_model": "claude-sonnet-5",
        "claude_effort": "medium",
    },
    "high": {
        "codex_worker": "high-worker",
        "codex_model": "gpt-5.6-sol",
        "codex_effort": "high",
        "claude_worker": "high-worker",
        "claude_model": "claude-opus-5",
        "claude_effort": "high",
    },
}


def fail(message: str) -> None:
    raise AssertionError(message)


def parse_tier_table(text: str) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    pattern = re.compile(
        r"^\| `(?P<tier>fast|standard|high)` "
        r"\| `(?P<codex_worker>[^`]+)` "
        r"\| `(?P<codex_model>[^`]+)`, `(?P<codex_effort>[^`]+)` "
        r"\| `(?P<claude_worker>[^`]+)` "
        r"\| `(?P<claude_model>[^`]+)`, `(?P<claude_effort>[^`]+)` \|$",
        re.MULTILINE,
    )
    for match in pattern.finditer(text):
        values = match.groupdict()
        tier = values.pop("tier")
        rows[tier] = values
    return rows


def parse_claude_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text()
    parts = text.split("---", 2)
    if len(parts) != 3:
        fail(f"{path}: missing YAML frontmatter")

    values: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def validate_profiles() -> None:
    model_tiers = (
        REPO_ROOT / "skills/orchestrator/references/MODEL_TIERS.md"
    ).read_text()
    actual_table = parse_tier_table(model_tiers)
    if actual_table != EXPECTED:
        fail(f"MODEL_TIERS.md mismatch:\nexpected={EXPECTED}\nactual={actual_table}")

    for tier, expected in EXPECTED.items():
        codex_path = REPO_ROOT / "agents" / f"{expected['codex_worker']}.toml"
        with codex_path.open("rb") as handle:
            codex = tomllib.load(handle)
        actual_codex = {
            "name": codex.get("name"),
            "model": codex.get("model"),
            "effort": codex.get("model_reasoning_effort"),
        }
        expected_codex = {
            "name": expected["codex_worker"],
            "model": expected["codex_model"],
            "effort": expected["codex_effort"],
        }
        if actual_codex != expected_codex:
            fail(
                f"{codex_path}: expected {expected_codex}, got {actual_codex}"
            )

        claude_path = (
            REPO_ROOT / "claude-agents" / f"{expected['claude_worker']}.md"
        )
        claude = parse_claude_frontmatter(claude_path)
        actual_claude = {
            "name": claude.get("name"),
            "model": claude.get("model"),
            "effort": claude.get("effort"),
        }
        expected_claude = {
            "name": expected["claude_worker"],
            "model": expected["claude_model"],
            "effort": expected["claude_effort"],
        }
        if actual_claude != expected_claude:
            fail(
                f"{claude_path}: expected {expected_claude}, got {actual_claude}"
            )


def validate_policy() -> None:
    protocol_path = REPO_ROOT / "skills/orchestrator/references/ORCHESTRATOR.md"
    protocol = protocol_path.read_text()
    required_protocol_text = [
        "V1 defines three abstract tiers:",
        "Every fresh bounded assignment starts at `fast`.",
        "`fast` → `standard` → `high`",
        "replacement may advance only to the next tier.",
        "it must not repeat `high`.",
        "model_tier: fast | standard | high",
        "runtime_enforcement: intended | confirmed",
    ]
    for required in required_protocol_text:
        if required not in protocol:
            fail(f"{protocol_path}: missing required policy text: {required}")

    skill_path = REPO_ROOT / "skills/orchestrator/SKILL.md"
    skill = skill_path.read_text()
    if "Resolve `fast`, `standard`, and `high`" not in skill:
        fail(f"{skill_path}: tier dispatch summary is stale")

    handoff_path = REPO_ROOT / "skills/factory-handoff/SKILL.md"
    handoff = handoff_path.read_text()
    if "model_tier: fast" not in handoff:
        fail(f"{handoff_path}: route example does not start at fast")
    if "attempted_model_tiers: [fast, standard]" not in handoff:
        fail(f"{handoff_path}: escalation history is not represented")

    stale_paths = [
        protocol_path,
        skill_path,
        REPO_ROOT / "skills/orchestrator/references/MODEL_TIERS.md",
    ]
    for path in stale_paths:
        if "high_reasoning" in path.read_text():
            fail(f"{path}: stale high_reasoning tier identifier")

    for stale_profile in [
        REPO_ROOT / "agents/high-reasoning-worker.toml",
        REPO_ROOT / "claude-agents/high-reasoning-worker.md",
    ]:
        if stale_profile.exists():
            fail(f"{stale_profile}: obsolete 2-tier worker still exists")


def main() -> int:
    try:
        validate_profiles()
        validate_policy()
    except (AssertionError, FileNotFoundError, tomllib.TOMLDecodeError) as error:
        print(f"model-tier validation failed: {error}", file=sys.stderr)
        return 1

    print("model-tier validation passed: fast -> standard -> high")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
