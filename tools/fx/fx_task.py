import json
import os
from pathlib import Path
import signal
import subprocess
import sys


def task_layout(task, orchestrator_agent=""):
    script = json.dumps(str(Path(__file__).resolve()), ensure_ascii=False)
    directory = json.dumps(str(task), ensure_ascii=False)
    agent = json.dumps(orchestrator_agent, ensure_ascii=False)
    return f'''layout {{
    default_tab_template {{
        pane size=1 borderless=true {{
            plugin location="tab-bar"
        }}
        children
        pane size=1 borderless=true {{
            plugin location="status-bar"
        }}
    }}
    tab {{
        pane command="python3" close_on_exit=true {{
            args {script} "shell" {directory} {agent}
        }}
    }}
}}
'''


def task_shell(task):
    os.chdir(task)
    session = os.environ.get("ZELLIJ_SESSION_NAME", f"{task.parent.parent.name}-{task.name}")
    print(f"Directory: {Path.cwd()}\nRepository: {task / 'repo'}\nZellij session: {session}", flush=True)
    for title, arguments in (
        ("Latest commit", ["log", "-1", "--format=%h %s"]),
        ("Git status", ["status", "--branch"]),
    ):
        print(f"\n{title}:", flush=True)
        try:
            result = subprocess.run(["git", "--no-pager", "-C", str(task / "repo"), *arguments], check=False)
            if result.returncode:
                print(f"fx: Could not read {title.lower()}.", file=sys.stderr)
        except OSError as error:
            print(f"fx: Could not read {title.lower()}: {error}", file=sys.stderr)
    print(flush=True)
    if sys.stdin.isatty():
        orchestrator = Path(__file__).resolve().parent / "commands/orchestrator"
        # Keep the pane alive while the orchestrator handles Ctrl+C.
        previous_handler = signal.signal(signal.SIGINT, lambda *_: None)
        try:
            subprocess.run([orchestrator], check=False)
        except OSError as error:
            print(f"fx: Could not start the orchestrator: {error}", file=sys.stderr)
        finally:
            signal.signal(signal.SIGINT, previous_handler)
    shell = os.environ.get("SHELL") or "/bin/bash"
    os.execvp(shell, [shell, "-i"])


def main():
    if not (len(sys.argv) == 3 and sys.argv[1] == "layout"
            or len(sys.argv) in (3, 4) and sys.argv[1] == "shell"):
        raise SystemExit("Usage: fx_task.py layout <task-directory> | shell <task-directory> [orchestrator-agent]")
    task = Path(sys.argv[2]).resolve(strict=True)
    if sys.argv[1] == "layout":
        print(task_layout(task, os.environ.get("FX_ORCHESTRATOR_AGENT", "")), end="")
    else:
        if len(sys.argv) == 4:
            os.environ["FX_ORCHESTRATOR_AGENT"] = sys.argv[3]
        task_shell(task)


if __name__ == "__main__":
    main()
