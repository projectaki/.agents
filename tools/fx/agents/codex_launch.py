import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fx_events import prepare_events
from fx_access import session_access
from codex_access import access_arguments
from fx_models import session_model, validate_model
from fx_usage import write_json
from openrouter_api import api_key, verify_model


def provider_arguments(provider):
    if not provider:
        return []
    if provider != "openrouter":
        raise ValueError(f"Unknown Codex provider: {provider}")
    definition = (
        '{name="OpenRouter",base_url="https://openrouter.ai/api/v1",'
        'wire_api="responses",auth={command="sh",args=["-c",'
        '"printf \'%s\' \\"$OPENROUTER_API_KEY\\""]}}'
    )
    return ["-c", 'model_provider="fx_openrouter"',
            "-c", f"model_providers.fx_openrouter={definition}"]


def launch(project, task, session, reasoning, prompt, model, provider):
    session = Path(session)
    adapter_dir = Path(__file__).resolve().parent
    events = prepare_events(session)
    descriptor = os.open(events / "codex-session.jsonl", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    with (events / "harness-version.txt").open("w") as version:
        subprocess.run(["codex", "--version"], stdout=version, check=True)
    capture = str(adapter_dir / "codex_capture.py")
    capture_config = subprocess.check_output([sys.executable, capture, "config", str(session)], text=True).strip()
    hooks = subprocess.check_output([sys.executable, capture, "hooks-config", str(session)], text=True).splitlines()
    instructions = (session / "instructions.md").read_text().rstrip("\n")
    command = ["codex", "--cd", task, "--model", model,
               "-c", f"model_reasoning_effort={json.dumps(reasoning)}",
               "-c", f"developer_instructions={json.dumps(instructions)}",
               "--add-dir", str(Path(project) / "project_context"),
               "-c", capture_config, "--no-daemon",
               *access_arguments(session_access(session)), *provider_arguments(provider)]
    for setting in hooks:
        command.extend(["-c", setting])
    if prompt:
        command.extend(["--", prompt[0]])
    with (session / "launch.txt").open("a") as metadata:
        metadata.write(f"model={model}\n")
        if provider:
            metadata.write(f"provider={provider}\n")
    environment = {**os.environ, "CODEX_TUI_RECORD_SESSION": "1",
                   "CODEX_TUI_SESSION_LOG_PATH": str(events / "codex-session.jsonl"),
                   "FX_SESSION_CONTEXT_DIR": str(session)}
    os.execvpe(command[0], command, environment)


def main():
    default, provider, action, *arguments = sys.argv[1:]
    try:
        if action == "model":
            print(validate_model(arguments[0] if arguments else default))
            return 0
        if not shutil.which("codex"):
            raise ValueError("Install Codex CLI before using this agent.")
        if provider:
            api_key()
        if action == "check":
            return 0
        if action not in ("launch", "batch") or not 4 <= len(arguments) <= 5:
            raise ValueError("Unsupported Codex adapter action or arguments.")
        project, task, session, reasoning, *prompt = arguments
        model = session_model(session, default)
        if provider:
            record = verify_model(model, parameters=("tools", "reasoning"))
            if action == "batch":
                write_json(Path(session) / "pricing.json", {
                    "model": model, "pricing": record.get("pricing", {}),
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "source": "https://openrouter.ai/api/v1/models",
                })
        if action == "batch":
            from codex_batch import run_batch
            if not prompt:
                raise ValueError("Batch execution requires an assignment.")
            return run_batch(project, task, session, reasoning, prompt[0], model, provider_arguments(provider), provider)
        launch(project, task, session, reasoning, prompt, model, provider)
    except subprocess.CalledProcessError as error:
        print(f"fx: Codex command failed with exit status {error.returncode}.", file=sys.stderr)
        return error.returncode
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"fx: Cannot start Codex agent: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
