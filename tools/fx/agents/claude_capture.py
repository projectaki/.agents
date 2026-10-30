import json
from pathlib import Path
import shlex
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fx_context import report_capture_error, save_response


def main():
    session = Path(sys.argv[2])
    if sys.argv[1] == "settings":
        command = shlex.join([sys.executable, str(Path(__file__).resolve()), "capture", str(session)])
        print(json.dumps({"hooks": {"Stop": [{"hooks": [{
            "type": "command", "command": command, "timeout": 30,
        }]}]}}))
        return 0
    try:
        event = json.load(sys.stdin)
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
