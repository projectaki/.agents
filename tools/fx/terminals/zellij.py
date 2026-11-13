import os
from pathlib import Path
import shutil
import subprocess
import sys


TOOL_DIR = Path(__file__).resolve().parents[1]


def probe():
    return "" if shutil.which("zellij") else None


def current():
    return os.environ.get("ZELLIJ_SESSION_NAME") if os.environ.get("ZELLIJ") else None


def label(workspace, name):
    return name


def find(name, session_id=None):
    result = subprocess.run(["zellij", "list-sessions", "--short", "--no-formatting"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode == 1 and result.stdout.strip() == "No active zellij sessions found.":
        return None
    if result.returncode:
        raise ValueError(f"Could not list Zellij sessions. {result.stdout.strip()}")
    return name if name in result.stdout.splitlines() else None


def legacy_session(name, background):
    if not background and current() == name:
        return name
    if probe() is None:
        return None
    if background:
        result = subprocess.run(["zellij", "--session", name, "action", "list-tabs"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return name if result.returncode == 0 else None
    return find(name)


def create(workspace, name, startup, background):
    if background:
        env = {key: value for key, value in os.environ.items()
               if key not in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID")}
        result = subprocess.run(["zellij", "attach", "--create-background", name,
                                 "options", "--default-cwd", str(workspace)],
                                env=env, stdout=sys.stderr)
        if result.returncode and not legacy_session(name, background=True):
            raise ValueError(f"Could not start Zellij review session {name}. Workspace: {workspace}")
    return name


def show(workspace, name, session_id):
    if current() == name:
        print(f"fx: Already in Zellij session: {name}", file=sys.stderr)
        return
    layout = subprocess.check_output([sys.executable, str(TOOL_DIR / "fx_task.py"),
                                      "layout", str(workspace)], text=True).rstrip("\n")
    if current():
        arguments = ["action", "switch-session", name, "--cwd", str(workspace), "--layout-string", layout]
    else:
        arguments = ["--layout-string", layout, "attach", "--create", name,
                     "options", "--default-cwd", str(workspace)]
    os.execvp("zellij", ["zellij", *arguments])


def hint(name, session_id):
    return f"Attach with: zellij attach {session_id}"


def tab(session_id, name, workspace, arguments, background):
    env = dict(os.environ)
    if background or env.get("FX_ZELLIJ_TAB_CLIENT") == "1":
        # Zellij 0.45.1 needs an attached client to size a background tab.
        env["FX_ZELLIJ_TAB_CLIENT"] = "1"
        command = [sys.executable, str(TOOL_DIR / "fx_zellij_client.py"), session_id]
        arguments = ["env", "FX_ZELLIJ_TAB_CLIENT=1", *arguments]
    else:
        command = ["zellij", "--session", session_id, "action", "new-tab"]
    return [*command, "--name", name, "--cwd", str(workspace), "--layout",
            str(TOOL_DIR / "templates/agent-tab.kdl"), "--", *arguments], env


def close(session_id):
    subprocess.run(["zellij", "delete-session", "--force", session_id], check=True)
