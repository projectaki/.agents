import argparse
from pathlib import Path
import re


def validate_model(model):
    if not isinstance(model, str) or not re.fullmatch(r"~?[a-zA-Z0-9][a-zA-Z0-9_./:-]*", model):
        raise ValueError("Model names must contain only letters, digits, underscores, dots, slashes, colons, hyphens, or a leading tilde.")
    return model


def model_slug(model):
    return re.sub(r"[/:~]", "-", validate_model(model)).lstrip("-")


def session_model(session, default):
    path = Path(session) / "model.txt"
    if path.is_symlink():
        raise ValueError("The session model must not be a symbolic link.")
    return validate_model(path.read_text().strip() if path.exists() else default)


def session_agent(session, default="codex"):
    path = Path(session) / "launch.txt"
    if not path.exists():
        return default
    metadata = dict(line.split("=", 1) for line in path.read_text().splitlines())
    return metadata.get("agent", default)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("validate", "slug"))
    parser.add_argument("model")
    args = parser.parse_args()
    try:
        print(model_slug(args.model) if args.action == "slug" else validate_model(args.model))
    except ValueError as error:
        parser.exit(1, f"fx: {error}\n")


if __name__ == "__main__":
    main()
