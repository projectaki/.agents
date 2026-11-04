import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fx_context import report_capture_error, save_response
from fx_events import prepare_events
from fx_models import session_agent, session_model


def final_response(path):
    conversation = None
    response = None
    completed = False
    with path.open() as stream:
        for line in stream:
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError("Expected a Codex event object.")
            kind = event.get("type")
            if kind in ("error", "turn.failed"):
                raise ValueError(f"Codex did not finish successfully: {event}")
            if kind == "thread.started":
                conversation = event.get("thread_id")
            item = event.get("item")
            if kind == "item.completed" and isinstance(item, dict) and item.get("type") == "agent_message":
                response = item.get("text")
            if kind == "turn.completed":
                completed = True
    if not completed or not isinstance(conversation, str) or not conversation or not isinstance(response, str) or not response.strip():
        raise ValueError("Codex returned no completed turn with a final response.")
    return conversation, response


def run_batch(project, task, session, reasoning, prompt, model=None, provider_args=(), provider=""):
    session = Path(session)
    try:
        adapter = Path(__file__).with_name("codex")
        model = model or session_model(session, subprocess.check_output([str(adapter), "model"], text=True).strip())
        events = prepare_events(session)
        with (events / "harness-version.txt").open("x") as version:
            subprocess.run(["codex", "--version"], stdout=version, check=True)
        instructions = (session / "instructions.md").read_text()
        capture_config = subprocess.check_output(
            [sys.executable, str(adapter.with_name("codex_capture.py")), "config", str(session)], text=True).strip()
        command = ["codex", "exec", "--dangerously-bypass-approvals-and-sandbox", "--cd", task, "--model", model,
                   "-c", f"model_reasoning_effort={json.dumps(reasoning)}",
                   "-c", f"developer_instructions={json.dumps(instructions)}",
                   "-c", capture_config,
                   "--add-dir", str(Path(project) / "project_context"),
                   "--skip-git-repo-check", "--json", *provider_args, "--", prompt]
        with (session / "launch.txt").open("a") as launch:
            launch.write(f"model={model}\n")
            if provider:
                launch.write(f"provider={provider}\n")
        output = events / "codex-exec.jsonl"
        with output.open("x") as stream:
            result = subprocess.run(command, cwd=task, stdin=subprocess.DEVNULL, stdout=stream,
                                    env={**os.environ, "FX_SESSION_CONTEXT_DIR": str(session)})
        if result.returncode:
            return result.returncode
        conversation, response = final_response(output)
        save_response(session, session_agent(session), conversation, "batch", response, capture_source="codex-exec")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        report_capture_error(session, error)
        return 1
    return 0


def main():
    return run_batch(*sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
