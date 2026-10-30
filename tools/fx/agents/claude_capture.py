import json
from pathlib import Path
import shlex
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fx_context import report_capture_error, save_response
from fx_events import capture_event


HOOK_EVENTS = (
    "SessionStart", "SessionEnd", "Setup", "InstructionsLoaded", "UserPromptSubmit",
    "UserPromptExpansion", "PreToolUse", "PermissionRequest", "PermissionDenied",
    "PostToolUse", "PostToolUseFailure", "PostToolBatch", "Notification", "MessageDisplay",
    "SubagentStart", "SubagentStop", "TaskCreated", "TaskCompleted", "Stop", "StopFailure",
    "TeammateIdle", "ConfigChange", "CwdChanged", "DirectoryAdded", "PreCompact",
    "PostCompact", "PreModelSwitch", "PostModelSwitch", "Elicitation", "ElicitationResult",
)


def main():
    session = Path(sys.argv[2])
    if sys.argv[1] == "settings":
        print(json.dumps({"hooks": {name: [{"hooks": [{
            "type": "command",
            "command": shlex.join([sys.executable, str(Path(__file__).resolve()),
                                   "capture" if name == "Stop" else "event", str(session)]),
            "timeout": 30,
        }]}] for name in HOOK_EVENTS}}))
        return 0
    raw_payload = sys.stdin.read()
    capture_event(session, "claude", "hook", raw_payload)
    if sys.argv[1] == "event":
        return 0
    try:
        event = json.loads(raw_payload)
        if not isinstance(event, dict):
            raise ValueError("Expected a completion event object.")
        if event.get("hook_event_name") != "Stop" or event.get("agent_id"):
            return 0
        result = save_response(session, "claude", event.get("session_id"),
                               event.get("prompt_id"), event.get("last_assistant_message"))
        print(json.dumps({"systemMessage": f"fx: Saved final response: {result / 'response.md'}"}))
        return 0
    except (OSError, ValueError, KeyError) as error:
        report_capture_error(session, error)
        print(json.dumps({"systemMessage": "fx: Response capture failed. Inspect capture-error.txt before handing off."}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
