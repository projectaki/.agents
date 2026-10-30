import json
import os
from pathlib import Path
import shlex
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fx_context import report_capture_error, save_response
from fx_events import capture_event


HOOK_EVENTS = (
    "SessionStart", "SessionEnd", "UserPromptSubmit", "PreToolUse", "PermissionRequest",
    "PostToolUse", "PreCompact", "PostCompact", "SubagentStart", "SubagentStop", "Stop", "Interrupt",
)


def main():
    if sys.argv[1] == "hook":
        session = Path(os.environ["FX_SESSION_CONTEXT_DIR"])
        capture_event(session, "codex", "hook", sys.stdin.read())
        print("{}")
        return 0
    session = Path(sys.argv[2])
    if sys.argv[1] == "hooks-config":
        command = shlex.join([sys.executable, str(Path(__file__).resolve()), "hook"])
        for name in HOOK_EVENTS:
            print(f"hooks.{name}=[{{hooks=[{{type=\"command\",command={json.dumps(command)},timeout=3}}]}}]")
        return 0
    if sys.argv[1] == "config":
        print("notify=" + json.dumps([
            sys.executable, str(Path(__file__).resolve()), "capture", str(session),
        ], ensure_ascii=False))
        return 0
    capture_event(session, "codex", "notify", sys.argv[3])
    try:
        event = json.loads(sys.argv[3])
        if not isinstance(event, dict):
            raise ValueError("Expected a completion event object.")
        if event.get("type") != "agent-turn-complete":
            return 0
        save_response(session, "codex", event.get("thread-id"),
                      event.get("turn-id"), event.get("last-assistant-message"))
        return 0
    except (OSError, ValueError, KeyError) as error:
        report_capture_error(session, error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
