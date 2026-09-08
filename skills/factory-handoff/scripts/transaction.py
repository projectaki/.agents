"""Recoverable publication of one checkpoint and its current documents."""

import json
import os


def replace_text(path, text):
    temporary = path.with_name(path.name + ".pending")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def recover(root):
    pending = root / "pending-checkpoint.json"
    if not pending.exists():
        return None
    update = json.loads(pending.read_text())
    history = root / "history.jsonl"
    lines = history.read_text().splitlines() if history.exists() else []
    record = update["record"]
    count = record["sequence"] - 1
    if len(lines) == count + 1 and json.loads(lines[-1]) == record:
        pending.unlink()
        return record
    if len(lines) != count:
        raise ValueError("Pending checkpoint conflicts with current history")
    for name, text in update["documents"].items():
        if name not in {"task.json", "assurance.json", "report.md"}:
            raise ValueError("Unexpected document in pending checkpoint")
        if text is None:
            (root / name).unlink(missing_ok=True)
        else:
            replace_text(root / name, text)
    replace_text(history, "".join(line + "\n" for line in lines) + json.dumps(record, separators=(",", ":")) + "\n")
    pending.unlink()
    return record


def publish(root, source, record):
    documents = {name: (source / name).read_text() if (source / name).exists() else None
                 for name in ("task.json", "assurance.json", "report.md")}
    replace_text(root / "pending-checkpoint.json", json.dumps(dict(record=record, documents=documents)))
    recover(root)
