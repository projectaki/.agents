import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fx_usage import unavailable_usage, validate_usage


def result_usage(result):
    if not isinstance(result, dict):
        raise ValueError("Expected a result object.")
    models = result.get("modelUsage", result.get("model_usage"))
    if models is not None and not isinstance(models, dict):
        raise ValueError("Invalid model usage.")
    notes = ["CLI cost is a client estimate of API usage, not a subscription charge or invoice."]
    if isinstance(models, dict) and models:
        fields = {"input_tokens": "inputTokens", "output_tokens": "outputTokens",
                  "cache_read_input_tokens": "cacheReadInputTokens",
                  "cache_creation_input_tokens": "cacheCreationInputTokens"}
        usage = {}
        for field, source in fields.items():
            values = [model.get(source) for model in models.values() if isinstance(model, dict)]
            if len(values) != len(models) or any(type(value) is not int or value < 0 for value in values):
                raise ValueError("Invalid per-model usage.")
            usage[field] = sum(values)
        scope = "All reported models, including subagents."
    else:
        usage = result.get("usage", {})
        if not isinstance(usage, dict):
            raise ValueError("Invalid token usage.")
        scope = "Main agent only; subagent token usage is unavailable without modelUsage."
        notes.append(scope)
    uncached = usage.get("input_tokens")
    cached = usage.get("cache_read_input_tokens")
    written = usage.get("cache_creation_input_tokens")
    for value in (uncached, cached, written):
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError("Invalid input usage.")
    total = None if any(value is None for value in (uncached, cached, written)) else uncached + cached + written
    cost = result.get("total_cost_usd")
    complete = (bool(models) and result.get("subtype") == "success" and not result.get("is_error")
                and total is not None and usage.get("output_tokens") is not None)
    return validate_usage({"input_tokens": total, "cached_input_tokens": cached,
                           "cache_write_input_tokens": written,
                           "output_tokens": usage.get("output_tokens"),
                           "reasoning_output_tokens": None,
                           "cost_usd": cost, "cost_kind": "estimated" if cost is not None else "unavailable",
                           "coverage": "complete" if complete else "partial",
                           "token_scope": scope,
                           "source": "events/claude-result.json",
                           "notes": notes})


def main():
    session = Path(sys.argv[1])
    try:
        path = session / "events/claude-result.json"
        if path.is_symlink():
            raise ValueError("Usage source must not be a symbolic link.")
        value = result_usage(json.loads(path.read_text()))
    except (OSError, ValueError) as error:
        value = unavailable_usage(f"Cannot read provider usage: {type(error).__name__}.")
    print(json.dumps(value, allow_nan=False))


if __name__ == "__main__":
    main()
