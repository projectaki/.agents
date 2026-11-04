import json
import os
from pathlib import Path
import subprocess
import sys


def task_layout(task):
    script = json.dumps(str(Path(__file__).resolve()), ensure_ascii=False)
    directory = json.dumps(str(task), ensure_ascii=False)
    return f'''layout {{
    pane size=1 borderless=true {{
        plugin location="tab-bar"
    }}
    pane command="python3" close_on_exit=true {{
        args {script} "shell" {directory}
    }}
    pane size=1 borderless=true {{
        plugin location="status-bar"
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
    shell = os.environ.get("SHELL") or "/bin/bash"
    os.execvp(shell, [shell, "-i"])


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("layout", "shell"):
        raise SystemExit("Usage: fx_task.py layout|shell <task-directory>")
    task = Path(sys.argv[2]).resolve(strict=True)
    if sys.argv[1] == "layout":
        print(task_layout(task), end="")
    else:
        task_shell(task)


if __name__ == "__main__":
    main()
