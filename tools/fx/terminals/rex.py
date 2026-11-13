import hashlib
import json
import os
import re
import shutil
import subprocess
import sys


def command(*arguments, timeout="10s"):
    # The worktree and terminal must be on the same machine.
    endpoint = os.environ.get("REX_SERVER", "")
    target = ["--server", endpoint] if endpoint.startswith("unix:///") else []
    return ["rex", "--autostart=false", "--timeout", timeout, *target, *arguments]


def environment():
    return {key: value for key, value in os.environ.items() if key != "REX_SERVER"}


def request(*arguments, timeout="10s"):
    result = subprocess.run(command(*arguments, timeout=timeout), env=environment(),
                            capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def probe():
    if not shutil.which("rex"):
        return None
    try:
        result = subprocess.run(command("whoami", "--json", timeout="2s"), env=environment(),
                                capture_output=True, text=True, timeout=4)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode:
        return None
    endpoint = json.loads(result.stdout)["endpoint"]
    if not endpoint.startswith("unix:///"):
        raise ValueError(f"Rex returned a non-local server endpoint: {endpoint}")
    return endpoint


def current():
    return os.environ.get("REX_SESSION") if os.environ.get("REX_BLOCK") else None


def label(workspace, name):
    suffix = hashlib.sha256(os.fsencode(workspace)).hexdigest()[:12]
    return f"{name[:115]}-{suffix}"


def find(name, session_id=None):
    sessions = request("session", "ls", "--json")["sessions"]
    if session_id:
        return session_id if any(session["session_id"] == session_id for session in sessions) else None
    matches = [session["session_id"] for session in sessions if session["label"] == name]
    if len(matches) > 1:
        raise ValueError(f"Multiple Rex sessions have the label {name}. Resolve the duplicate sessions and retry.")
    return matches[0] if matches else None


def legacy_session(name, background):
    return None


def interactive_options(*subcommand):
    result = subprocess.run(command(*subcommand, "--help"), env=environment(),
                            capture_output=True, text=True, check=True, timeout=4)
    return ["--interactive"] if re.search(r"(?m)^\s*--interactive\s", result.stdout) else []


def create(workspace, name, startup, background):
    options = [*interactive_options("session", "new"), "--window", "Task", "--", *startup] if startup else []
    return request("session", "new", name, "--cwd", str(workspace),
                   "--json", *options)["session_id"]


def show(workspace, name, session_id):
    if current() == session_id:
        return
    try:
        client = os.environ.get("REX_CLIENT")
        if not client:
            clients = request("client", "ls", "--json", timeout="2s")["clients"]
            apps = [entry["client_id"] for entry in clients
                    if entry["info"].get("kind") == "app" and entry.get("connection_state") == "connected"]
            if len(apps) != 1:
                print(hint(name, session_id), file=sys.stderr)
                return
            client = apps[0]
        result = subprocess.run(command("--client", client, "do", "session.select",
                                        f"session_id={session_id}", timeout="2s"),
                                env=environment(), capture_output=True, text=True)
        if result.returncode:
            print(f"fx: Rex could not select the session in the app. {result.stderr.strip()}", file=sys.stderr)
            print(hint(name, session_id), file=sys.stderr)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"fx: Rex could not select the session in the app. {error}", file=sys.stderr)
        print(hint(name, session_id), file=sys.stderr)


def hint(name, session_id):
    return f"Open Rex session {name} ({session_id}) on this host."


def tab(session_id, name, workspace, arguments, background):
    terminal_command = command("window", "new", "--session", session_id, name,
                               "--cwd", str(workspace), *interactive_options("window", "new"))
    if background:
        terminal_command.append("--focus=false")
    return [*terminal_command, "--", *arguments], environment()


def close(session_id):
    subprocess.run(command("session", "kill", session_id), env=environment(), check=True)
