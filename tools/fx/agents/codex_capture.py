import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fx_context import report_capture_error, save_response


def main():
    session = Path(sys.argv[2])
    if sys.argv[1] == "config":
        print("notify=" + json.dumps([
            sys.executable, str(Path(__file__).resolve()), "capture", str(session),
        ], ensure_ascii=False))
        return 0
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
