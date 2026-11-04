import json
import os
from pathlib import Path
import shlex
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fx_context import report_capture_error, save_response
from fx_events import capture_event
from fx_models import session_agent


HOOK_EVENTS = (
    "SessionStart", "SessionEnd", "UserPromptSubmit", "PreToolUse", "PermissionRequest",
    "PostToolUse", "PreCompact", "PostCompact", "SubagentStart", "SubagentStop", "Stop", "Interrupt",
)


def main():
    if sys.argv[1] == "hook":
        session = Path(os.environ["FX_SESSION_CONTEXT_DIR"])
        raw_payload = sys.stdin.read()
        capture_event(session, session_agent(session), "hook", raw_payload)
        try:
            event = json.loads(raw_payload)
        except ValueError:
            print("{}")
            return 0
        try:
            if isinstance(event, dict) and event.get("hook_event_name") == "Stop" and not event.get("agent_id"):
                save_response(session, session_agent(session), event.get("session_id"),
                              event.get("turn_id"), event.get("last_assistant_message"))
        except (OSError, ValueError, KeyError) as error:
            report_capture_error(session, error)
            print(json.dumps({"systemMessage": "fx: Response capture failed. Inspect capture-error.txt before handing off."}))
            return 1
        print("{}")
        return 0
    session = Path(sys.argv[2])
    if sys.argv[1] == "hooks-config":
        command = shlex.join([sys.executable, str(Path(__file__).resolve()), "hook"])
        for name in HOOK_EVENTS:
            timeout = 30 if name == "Stop" else 3
            print(f"hooks.{name}=[{{hooks=[{{type=\"command\",command={json.dumps(command)},timeout={timeout}}}]}}]")
        return 0
    if sys.argv[1] == "config":
        print("notify=" + json.dumps([
            sys.executable, str(Path(__file__).resolve()), "capture", str(session),
        ], ensure_ascii=False))
        return 0
    capture_event(session, session_agent(session), "notify", sys.argv[3])
    return 0


if __name__ == "__main__":
    sys.exit(main())
