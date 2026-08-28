#!/usr/bin/env python3
"""Validate the canonical Factory proof ledger."""

from __future__ import annotations

import re
import sys
from datetime import date, datetime
from pathlib import Path

import yaml


METHODS = {"automated", "inspection", "visual", "manual"}
VERDICTS = {"unverified", "pass", "fail", "inconclusive", "waived"}
STATUSES = {"active", "superseded", "invalidated"}
UNIVERSAL = re.compile(r"\b(?:all|every|each)\b", re.IGNORECASE)


def require_nonempty_string(value: object, path: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path} must be a nonempty string")


def require_timestamp(value: object, path: str, errors: list[str]) -> None:
    if isinstance(value, (datetime, date)):
        return
    require_nonempty_string(value, path, errors)


def validate_exception(
    value: object,
    path: str,
    claim_id: object,
    claim_path_ids: object,
    errors: list[str],
) -> bool:
    if value is None:
        return False
    if not isinstance(value, dict):
        errors.append(f"{path} must be null or an object")
        return False
    if value.get("status") != "accepted":
        errors.append(f"{path}.status must be accepted")
    for field in ("claim_ids", "path_ids"):
        if not isinstance(value.get(field), list) or not value[field]:
            errors.append(f"{path}.{field} must be a nonempty list")
    if isinstance(value.get("claim_ids"), list) and claim_id not in value["claim_ids"]:
        errors.append(f"{path}.claim_ids must include its current claim")
    if isinstance(value.get("path_ids"), list) and isinstance(claim_path_ids, list):
        unknown_paths = sorted(set(value["path_ids"]) - set(claim_path_ids))
        if unknown_paths:
            errors.append(f"{path}.path_ids contains paths outside its claim: {', '.join(unknown_paths)}")
    require_nonempty_string(value.get("approval_reference"), f"{path}.approval_reference", errors)
    require_nonempty_string(value.get("residual_risk"), f"{path}.residual_risk", errors)
    return value.get("status") == "accepted"


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        return [f"cannot read valid YAML: {error}"]
    if not isinstance(document, dict):
        return ["ledger must be a YAML object"]
    if document.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    revision = document.get("task_revision")
    if not isinstance(revision, int) or revision < 1:
        errors.append("task_revision must be a positive integer")
    require_timestamp(document.get("updated_at"), "updated_at", errors)
    claims = document.get("claims")
    if not isinstance(claims, list) or not claims:
        errors.append("claims must be a nonempty list")
        return errors

    claim_ids: set[str] = set()
    proof_ids: set[str] = set()
    for claim_index, claim in enumerate(claims):
        claim_path = f"claims[{claim_index}]"
        if not isinstance(claim, dict):
            errors.append(f"{claim_path} must be an object")
            continue
        claim_id = claim.get("claim_id")
        require_nonempty_string(claim_id, f"{claim_path}.claim_id", errors)
        if isinstance(claim_id, str):
            if claim_id in claim_ids:
                errors.append(f"duplicate claim_id {claim_id}")
            claim_ids.add(claim_id)
        statement = claim.get("statement")
        require_nonempty_string(statement, f"{claim_path}.statement", errors)
        require_nonempty_string(claim.get("source"), f"{claim_path}.source", errors)
        if claim.get("status") not in STATUSES:
            errors.append(f"{claim_path}.status must be one of {sorted(STATUSES)}")
        for field in ("path_ids", "risk_ids"):
            if not isinstance(claim.get(field), list):
                errors.append(f"{claim_path}.{field} must be a list")

        if claim.get("status") == "active" and isinstance(statement, str) and UNIVERSAL.search(statement):
            inventory = claim.get("inventory")
            if not isinstance(inventory, dict) or inventory.get("status") != "closed":
                errors.append(f"{claim_path}.inventory must be closed for a universal claim")
            elif not isinstance(inventory.get("items"), list) or not inventory["items"]:
                errors.append(f"{claim_path}.inventory.items must be nonempty")
            else:
                inventory_ids: set[str] = set()
                for item_index, item in enumerate(inventory["items"]):
                    item_path = f"{claim_path}.inventory.items[{item_index}]"
                    if not isinstance(item, dict):
                        errors.append(f"{item_path} must be an object")
                        continue
                    for field in ("item_id", "name", "source"):
                        require_nonempty_string(item.get(field), f"{item_path}.{field}", errors)
                    item_id = item.get("item_id")
                    if isinstance(item_id, str):
                        if item_id in inventory_ids:
                            errors.append(f"duplicate inventory item_id {item_id} in {claim_id}")
                        inventory_ids.add(item_id)

        obligations = claim.get("proof_obligations")
        if not isinstance(obligations, list) or not obligations:
            errors.append(f"{claim_path}.proof_obligations must be a nonempty list")
            continue
        for proof_index, proof in enumerate(obligations):
            proof_path = f"{claim_path}.proof_obligations[{proof_index}]"
            if not isinstance(proof, dict):
                errors.append(f"{proof_path} must be an object")
                continue
            proof_id = proof.get("proof_id")
            require_nonempty_string(proof_id, f"{proof_path}.proof_id", errors)
            if isinstance(proof_id, str):
                if proof_id in proof_ids:
                    errors.append(f"duplicate proof_id {proof_id}")
                proof_ids.add(proof_id)
            require_nonempty_string(proof.get("requirement"), f"{proof_path}.requirement", errors)
            required_method = proof.get("required_method")
            planned_method = proof.get("planned_method")
            if required_method not in METHODS:
                errors.append(f"{proof_path}.required_method must be one of {sorted(METHODS)}")
            if planned_method not in METHODS:
                errors.append(f"{proof_path}.planned_method must be one of {sorted(METHODS)}")
            accepted_exception = validate_exception(
                proof.get("exception"),
                f"{proof_path}.exception",
                claim_id,
                claim.get("path_ids"),
                errors,
            )
            if required_method in METHODS and planned_method in METHODS and required_method != planned_method and not accepted_exception:
                errors.append(f"{proof_path} changes the required proof method without an accepted exception")
            evidence = proof.get("evidence")
            if not isinstance(evidence, list):
                errors.append(f"{proof_path}.evidence must be a list")
                evidence = []
            for evidence_index, entry in enumerate(evidence):
                evidence_path = f"{proof_path}.evidence[{evidence_index}]"
                if not isinstance(entry, dict):
                    errors.append(f"{evidence_path} must be an object")
                    continue
                if entry.get("method") not in METHODS:
                    errors.append(f"{evidence_path}.method must be one of {sorted(METHODS)}")
                for field in ("result", "revision", "reference"):
                    require_nonempty_string(entry.get(field), f"{evidence_path}.{field}", errors)
            verdict = proof.get("verdict")
            if verdict not in VERDICTS:
                errors.append(f"{proof_path}.verdict must be one of {sorted(VERDICTS)}")
            if verdict == "waived" and not accepted_exception:
                errors.append(f"{proof_path} has a waived verdict without an accepted exception")
            if verdict == "pass" and not evidence:
                errors.append(f"{proof_path} has a pass verdict without evidence")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate-proof-ledger.py <proof-ledger.yaml>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"proof ledger not found: {path}", file=sys.stderr)
        return 2
    errors = validate(path)
    if errors:
        for error in errors:
            print(f"{path}: {error}", file=sys.stderr)
        return 1
    print(f"Proof ledger is valid: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
