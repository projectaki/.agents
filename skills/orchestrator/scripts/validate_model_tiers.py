#!/usr/bin/env python3
"""Validate the orchestrator's three-tier model policy."""

from __future__ import annotations

import argparse
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
EXPECTED_CODEX_PROFILES = {
    f"{values['codex_worker']}.toml" for values in EXPECTED.values()
}
EXPECTED_CLAUDE_PROFILES = {
    f"{values['claude_worker']}.md" for values in EXPECTED.values()
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

    codex_directory = REPO_ROOT / "agents"
    actual_codex_profiles = {
        path.name for path in codex_directory.iterdir() if path.is_file()
    }
    if actual_codex_profiles != EXPECTED_CODEX_PROFILES:
        fail(
            "Codex agent directory must contain exactly the three tier profiles:"
            f"\nexpected={sorted(EXPECTED_CODEX_PROFILES)}"
            f"\nactual={sorted(actual_codex_profiles)}"
        )

    claude_directory = REPO_ROOT / "claude-agents"
    actual_claude_profiles = {
        path.name for path in claude_directory.iterdir() if path.is_file()
    }
    if actual_claude_profiles != EXPECTED_CLAUDE_PROFILES:
        fail(
            "Claude agent directory must contain exactly the three tier profiles:"
            f"\nexpected={sorted(EXPECTED_CLAUDE_PROFILES)}"
            f"\nactual={sorted(actual_claude_profiles)}"
        )

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
        "dispatch_mechanism: native_profile",
        "runtime_enforcement: confirmed",
    ]
    for required in required_protocol_text:
        if required not in protocol:
            fail(f"{protocol_path}: missing required policy text: {required}")

    skill_path = REPO_ROOT / "skills/orchestrator/SKILL.md"
    skill = skill_path.read_text()
    if "Resolve `fast`, `standard`, and `high`" not in skill:
        fail(f"{skill_path}: tier dispatch summary is stale")
    if "Use only the `fast-worker`, `standard-worker`, and `high-worker` profiles." not in skill:
        fail(f"{skill_path}: exclusive tier-profile policy is missing")
    if "Do not invoke `$codex-cli`,\n  `$claude-cli`" not in skill:
        fail(f"{skill_path}: native-only dispatch policy is missing")
    required_receipt_text = [
        "Routing selected: <lifecycle> -> <tier> -> <worker-profile>",
        "Started: <worker-profile> for <lifecycle>",
        "Only after native spawn succeeds",
    ]
    for required in required_receipt_text:
        if required not in skill:
            fail(f"{skill_path}: dispatch receipt is missing: {required}")

    handoff_path = REPO_ROOT / "skills/factory-handoff/SKILL.md"
    handoff = handoff_path.read_text()
    if "model_tier: fast" not in handoff:
        fail(f"{handoff_path}: route example does not start at fast")
    if "attempted_model_tiers: [fast, standard]" not in handoff:
        fail(f"{handoff_path}: escalation history is not represented")
    if "dispatch_mechanism: native_profile" not in handoff:
        fail(f"{handoff_path}: dispatch mechanism is not represented")

    forbidden_role_profiles = [
        "architect-planner",
        "bug-reproducer",
        "context-researcher",
        "maintainability-reviewer",
        "plan-reviewer",
        "release-manager",
        "requirements-analyst",
        "security-reviewer",
        "user-simulator",
        "verification-engineer",
    ]
    factory_skills = "\n".join(
        path.read_text()
        for path in (REPO_ROOT / "skills").glob("factory-*/SKILL.md")
    )
    for profile in forbidden_role_profiles:
        if f"`{profile}`" in factory_skills:
            fail(f"Factory skills still dispatch removed role profile: {profile}")

    actor_skill_names = [
        "factory-context",
        "factory-replicate",
        "factory-test-scope",
        "factory-plan",
        "factory-implement",
        "factory-review",
        "factory-regression-scope",
        "factory-video-evidence",
        "factory-verify",
        "factory-draft-pr",
        "factory-learn",
    ]
    execution_boundary = (
        "the primary thread must spawn the tier worker\n"
        "selected by routing"
    )
    for actor_skill_name in actor_skill_names:
        actor_skill = REPO_ROOT / "skills" / actor_skill_name / "SKILL.md"
        if execution_boundary not in actor_skill.read_text():
            fail(f"{actor_skill}: native tier-worker execution boundary is missing")

    tier_policy = (
        REPO_ROOT / "skills/orchestrator/references/MODEL_TIERS.md"
    ).read_text()
    if "Do not invoke `$codex-cli`, `$claude-cli`" not in tier_policy:
        fail("MODEL_TIERS.md does not prohibit CLI fallback")
    if "Routing selected: REVIEW -> high -> high-worker" not in tier_policy:
        fail("MODEL_TIERS.md does not show the human-visible dispatch receipt")

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


def validate_installation() -> None:
    installed_directories = {
        "Codex": Path.home() / ".codex" / "agents",
        "Claude": Path.home() / ".claude" / "agents",
    }
    expected_directories = {
        "Codex": REPO_ROOT / "agents",
        "Claude": REPO_ROOT / "claude-agents",
    }
    for runtime, installed in installed_directories.items():
        if not installed.exists():
            fail(f"{runtime} agent directory is not installed: {installed}")
        if installed.resolve() != expected_directories[runtime].resolve():
            fail(
                f"{runtime} agent directory does not resolve to the canonical profiles:"
                f"\ninstalled={installed.resolve()}"
                f"\nexpected={expected_directories[runtime].resolve()}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-installation",
        action="store_true",
        help="Also verify that Codex and Claude discover these canonical profile directories.",
    )
    args = parser.parse_args()

    try:
        validate_profiles()
        validate_policy()
        if args.check_installation:
            validate_installation()
    except (AssertionError, FileNotFoundError, tomllib.TOMLDecodeError) as error:
        print(f"model-tier validation failed: {error}", file=sys.stderr)
        return 1

    suffix = " with installed profile links" if args.check_installation else ""
    print(f"model-tier validation passed: fast -> standard -> high{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
