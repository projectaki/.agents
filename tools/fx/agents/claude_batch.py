import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fx_context import captured_results, report_capture_error, response_metadata, save_response
from fx_events import prepare_events


def final_response(path):
    result = json.loads(path.read_text())
    if not isinstance(result, dict) or result.get("is_error") or result.get("subtype") != "success":
        raise ValueError("Claude did not complete the investigation successfully.")
    denials = result.get("permission_denials", [])
    if not isinstance(denials, list) or any(
            not isinstance(item, dict) or not isinstance(item.get("tool_name"), str) for item in denials):
        raise ValueError("Claude returned invalid permission-denial details.")
    if denials:
        tools = sorted({item["tool_name"] for item in denials})
        raise ValueError("Claude encountered permission denials: " + ", ".join(tools)
                         + ". The provider response is preserved for diagnosis.")
    conversation, response = result.get("session_id"), result.get("result")
    if not isinstance(conversation, str) or not conversation or not isinstance(response, str) or not response.strip():
        raise ValueError("Claude returned no conversation ID or final response.")
    return conversation, response


def main():
    project, task, session, reasoning, prompt = sys.argv[1:]
    session = Path(session)
    try:
        adapter = Path(__file__).with_name("claude")
        model = subprocess.check_output([str(adapter), "model"], text=True).strip()
        events = prepare_events(session)
        with (events / "harness-version.txt").open("x") as version:
            subprocess.run(["claude", "--version"], stdout=version, check=True)
        settings = session / "claude-settings.json"
        with settings.open("x") as stream:
            subprocess.run([sys.executable, str(adapter.with_name("claude_capture.py")), "settings", str(session)],
                           stdout=stream, check=True)
        command = ["claude", "--model", model, "--effort", reasoning,
                   "--append-system-prompt-file", str(session / "instructions.md"),
                   "--add-dir", project,
                   "--settings", str(settings),
                   "--debug-file", str(events / "claude-debug.log"),
                   "--print", "--output-format", "json", "--permission-prompts", "none",
                   "--permission-mode", "auto",
                   "--", prompt]
        with (session / "launch.txt").open("a") as launch:
            launch.write(f"model={model}\n")
        output = events / "claude-result.json"
        with output.open("x") as stream:
            result = subprocess.run(command, cwd=task, stdin=subprocess.DEVNULL, stdout=stream,
                                    env={**os.environ, "FX_SESSION_CONTEXT_DIR": str(session)})
        if result.returncode:
            return result.returncode
        conversation, response = final_response(output)
        previous = captured_results(session)
        captured = previous[-1] if previous else None
        if (captured is None
                or response_metadata(captured).get("conversation_id") != conversation
                or (captured / "response.md").read_text() != response):
            save_response(session, "claude", conversation, "batch", response, capture_source="claude-print")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        report_capture_error(session, error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
