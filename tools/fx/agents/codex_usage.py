from decimal import Decimal, InvalidOperation
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fx_usage import TOKEN_FIELDS, unavailable_usage, validate_usage


def estimate_cost(usage, pricing):
    fields = ("input_tokens", "cached_input_tokens", "output_tokens")
    if any(usage.get(field) is None for field in fields):
        return None
    try:
        rates = [Decimal(pricing[key]) for key in ("prompt", "completion")]
        cached = usage["cached_input_tokens"]
        cache_rate = Decimal(pricing["input_cache_read"]) if cached else Decimal(0)
        if any(not rate.is_finite() or rate < 0 for rate in (*rates, cache_rate)):
            return None
        cost = (usage["input_tokens"] - cached) * rates[0] + cached * cache_rate + usage["output_tokens"] * rates[1]
        value = float(cost)
        return value if math.isfinite(value) else None
    except (KeyError, TypeError, InvalidOperation, ValueError):
        return None


def event_usage(lines, pricing=None):
    records = []
    partial = False
    for line in lines:
        try:
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError("Invalid event.")
            if event.get("type") in ("turn.failed", "error"):
                partial = True
            if event.get("type") != "turn.completed":
                continue
            raw = event.get("usage")
            if not isinstance(raw, dict):
                partial = True
                continue
            value = {field: raw.get(field) for field in TOKEN_FIELDS}
            value.update(cost_usd=raw.get("cost"), cost_kind="reported" if raw.get("cost") is not None else "unavailable",
                         coverage="complete" if raw.get("input_tokens") is not None and raw.get("output_tokens") is not None else "partial", notes=[])
            records.append(validate_usage(value))
        except (ValueError, TypeError):
            partial = True
    if not records:
        return unavailable_usage("No completed turn contains usable token usage.")
    totals = {}
    for field in TOKEN_FIELDS:
        counts = [record.get(field) for record in records]
        totals[field] = sum(counts) if all(count is not None for count in counts) else None
    cost = sum(record["cost_usd"] for record in records) if all(record["cost_usd"] is not None for record in records) else None
    kind = "reported" if cost is not None else "unavailable"
    notes = []
    if cost is None and pricing is not None:
        cost = estimate_cost(totals, pricing)
        kind = "estimated" if cost is not None else "unavailable"
        notes.append("Estimate uses the saved catalog base rates; excludes time discounts, tier changes, cache-write surcharges, tool fees, and account adjustments.")
    if cost is None:
        notes.append("The CLI supplied no dollar cost, or the data is insufficient to estimate it. Subscription charges are not inferred.")
    if partial:
        notes.append("Some events were failed, missing usage, or unreadable. Counts cover only usable completed turns.")
    return validate_usage({**totals, "cost_usd": cost, "cost_kind": kind,
                           "coverage": "partial" if partial or totals["input_tokens"] is None or totals["output_tokens"] is None else "complete",
                           "source": "events/codex-exec.jsonl", "notes": notes})


def main():
    session = Path(sys.argv[1])
    try:
        pricing = None
        snapshot = session / "pricing.json"
        pricing_note = None
        if snapshot.exists() or snapshot.is_symlink():
            try:
                if snapshot.is_symlink():
                    raise ValueError("Pricing must not be a symbolic link.")
                pricing = json.loads(snapshot.read_text())["pricing"]
                if not isinstance(pricing, dict):
                    raise ValueError("Invalid pricing.")
            except (OSError, ValueError, KeyError, TypeError):
                pricing = None
                pricing_note = "Pricing snapshot is unreadable; token usage is still available."
        path = session / "events/codex-exec.jsonl"
        if path.is_symlink():
            raise ValueError("Usage source must not be a symbolic link.")
        with path.open() as stream:
            value = event_usage(stream, pricing)
        if pricing_note:
            value["notes"].append(pricing_note)
    except (OSError, ValueError, KeyError, TypeError) as error:
        value = unavailable_usage(f"Cannot read provider usage: {type(error).__name__}.")
    print(json.dumps(value, allow_nan=False))


if __name__ == "__main__":
    main()
