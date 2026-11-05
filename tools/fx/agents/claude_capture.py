import json
from pathlib import Path
import re
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


def resume_id(session):
    session = Path(session)
    identities = set()
    events = session / "events"
    path = events / "callbacks.jsonl"
    if events.is_symlink() or path.is_symlink():
        raise ValueError("Conversation records must not be symbolic links.")
    if path.exists():
        with path.open() as stream:
            for line in stream:
                if not line.endswith("\n"):
                    raise ValueError("The callback log has an incomplete last record. Preserve it before repairing capture.")
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(record, dict) or record.get("agent") != "claude":
                    continue
                event = record.get("payload")
                if not isinstance(event, dict) or event.get("agent_id"):
                    continue
                identity = event.get("session_id")
                if isinstance(identity, str) and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", identity):
                    identities.add(identity)
    results = session / "results"
    if results.is_symlink():
        raise ValueError("Conversation results must not be symbolic links.")
    for directory in sorted(results.glob("turn-*")):
        path = directory / "metadata.json"
        if directory.is_symlink() or path.is_symlink():
            raise ValueError("Conversation metadata must not be symbolic links.")
        metadata = json.loads(path.read_text())
        if not isinstance(metadata, dict):
            raise ValueError(f"Expected conversation metadata in {path}.")
        identity = metadata.get("conversation_id")
        if metadata.get("agent") == "claude" and isinstance(identity, str) and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", identity):
            identities.add(identity)
    if len(identities) != 1:
        raise ValueError("The session needs exactly one recorded Claude conversation identifier. No conversation was selected.")
    return identities.pop()


def main():
    session = Path(sys.argv[2])
    if sys.argv[1] == "resume-id":
        try:
            print(resume_id(session))
        except (OSError, ValueError) as error:
            print(f"fx: Cannot identify the Claude conversation: {error}", file=sys.stderr)
            return 1
        return 0
    if sys.argv[1] == "disable-sandbox":
        path = session / "claude-settings.json"
        try:
            settings = json.loads(path.read_text())
            if not isinstance(settings, dict):
                raise ValueError("Expected a Claude settings object.")
            sandbox = settings.setdefault("sandbox", {})
            if not isinstance(sandbox, dict):
                raise ValueError("Expected a sandbox settings object.")
            if sandbox.get("enabled") is not False:
                sandbox["enabled"] = False
                path.write_text(json.dumps(settings) + "\n")
        except (OSError, ValueError) as error:
            print(f"fx: Cannot disable the Claude sandbox: {error}", file=sys.stderr)
            return 1
        return 0
    if sys.argv[1] == "settings":
        print(json.dumps({"sandbox": {"enabled": False}, "hooks": {name: [{"hooks": [{
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
