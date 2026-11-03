import argparse
import json
from pathlib import Path
import re
import sys

from fx_context import prepare_context


def resolve_group(task, name):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", name):
        raise ValueError("Supply a group name, not a path.")
    root = Path(task).resolve(strict=True) / "context/groups"
    if root.is_symlink():
        raise ValueError("The groups directory must not be a symbolic link.")
    exact = root / name
    candidates = [exact] if exact.exists() else [
        path for path in root.iterdir()
        if (re.fullmatch(rf"[0-9]+-{re.escape(name)}", path.name)
            or re.fullmatch(rf"{re.escape(name)}-[a-zA-Z0-9]{{8}}", path.name))
        and (path / "group.md").is_file()
    ]
    if not candidates:
        raise ValueError(f"Group not found in this task: {name}")
    if len(candidates) > 1:
        choices = ", ".join(sorted(path.name for path in candidates))
        raise ValueError(f"Group name is ambiguous. Supply one full name: {choices}")
    group = candidates[0]
    if group.is_symlink() or not (group / "group.md").is_file():
        raise ValueError(f"Expected a group directory: {group}")
    return group


def comparison_context(task, group):
    for member in group.iterdir():
        if member.is_dir() and (member / "instructions.md").is_file():
            request = member / "tab-request.txt"
            if request.exists() and request.read_text().strip() != "accepted":
                raise ValueError(f"The tab request for {member.name} was not accepted. Inspect {request}.")
    context = prepare_context(task, [group])
    subject = group / "source.json"
    if subject.is_symlink():
        raise ValueError("The group source record must not be a symbolic link.")
    if subject.exists():
        identity = json.loads(subject.read_text())
        context += "\n## Original group source identity\n\n" + json.dumps(identity) + "\n"
        context += "Compare this identity with the current source before using review conclusions. A hash records content; it does not preserve a source copy.\n"
    else:
        context += "\nThe legacy group has no recorded source identity. Its reviewed source is unverified.\n"
    return context


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("resolve", "context"))
    parser.add_argument("task")
    parser.add_argument("name")
    args = parser.parse_args()
    try:
        group = resolve_group(args.task, args.name)
        if args.action == "resolve":
            print(group)
        else:
            print(comparison_context(args.task, group), end="")
    except (OSError, ValueError, KeyError) as error:
        print(f"fx: Cannot compare group: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
