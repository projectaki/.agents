import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys

from fx_usage import write_json
from terminals import BACKENDS


TOOL_DIR = Path(__file__).resolve().parent
RECORD_NAME = ".fx-terminal.json"


def backend_order():
    preference = os.environ.get("FX_MULTIPLEXER", "auto")
    if preference == "auto":
        return tuple(BACKENDS)
    if preference not in BACKENDS:
        raise ValueError(f"FX_MULTIPLEXER must be auto or one of: {', '.join(BACKENDS)}.")
    return (preference,)


def current_terminal():
    backend_name = os.environ.get("FX_TERMINAL_BACKEND")
    session_id = os.environ.get("FX_TERMINAL_SESSION")
    if backend_name in BACKENDS and session_id:
        return backend_name, session_id

    # A Zellij pane inside Rex inherits the Rex environment.
    for name in reversed(BACKENDS):
        session = BACKENDS[name].current()
        if session:
            return name, session
    backends = " or ".join(name.title() for name in BACKENDS)
    raise ValueError(f"Run this command inside a {backends} session. Use fx task <task_name> to open one.")


def require_terminal():
    name, session = current_terminal()
    if BACKENDS[name].probe() is None:
        raise ValueError(f"Install or reconnect {name.title()} to use terminal session {session}.")
    return name, session


def tab_command(name, workspace, arguments):
    backend_name, session_id = current_terminal()
    return BACKENDS[backend_name].tab(session_id, name, workspace, arguments,
                                      background=bool(os.environ.get("FX_TERMINAL_SESSION")))


def group_terminal():
    name, session = require_terminal()
    return getattr(BACKENDS[name], "group_pane", None), session


def saved_terminal(workspace):
    try:
        record = json.loads((workspace / RECORD_NAME).read_text())
    except FileNotFoundError:
        return None
    if (not isinstance(record, dict) or not isinstance(record.get("backend"), str)
            or record["backend"] not in BACKENDS
            or not isinstance(record.get("name"), str)
            or (record.get("id") is not None and not isinstance(record["id"], str))
            or (record.get("connection") is not None and not isinstance(record["connection"], str))):
        raise ValueError(f"Invalid terminal session record in {workspace / RECORD_NAME}.")
    return record


def find_saved(record):
    backend = BACKENDS[record["backend"]]
    target = record.get("id") or record["name"]
    connection = backend.probe()
    if connection is None:
        raise ValueError(f"Reconnect {record['backend'].title()} to check terminal session {target}.")
    if record.get("connection", "") != connection:
        raise ValueError(f"Reconnect to {record['connection']} to check terminal session {target}.")
    return backend.find(record["name"], record.get("id"))


def ensure_terminal(workspace, task_name, background):
    preference = backend_order()
    directory = os.open(workspace, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(directory, fcntl.LOCK_EX)
        record = saved_terminal(workspace)
        if record:
            session_id = find_saved(record)
            if session_id:
                if session_id != record.get("id"):
                    write_json(workspace / RECORD_NAME, {**record, "id": session_id})
                return record["backend"], record["name"], session_id

        for name, backend in BACKENDS.items():
            session_id = backend.legacy_session(task_name, background)
            if session_id:
                write_json(workspace / RECORD_NAME, {"backend": name, "name": task_name, "id": session_id})
                return name, task_name, session_id

        for name in preference:
            backend = BACKENDS[name]
            connection = backend.probe()
            if connection is not None:
                break
        else:
            raise ValueError(f"No terminal backend is available ({', '.join(preference)}). "
                             "For worktree preparation, use fx task --no-attach.")

        name_on_server = backend.label(workspace, task_name)
        startup = [] if background else [sys.executable, str(TOOL_DIR / "fx_task.py"),
                                         "shell", str(workspace), os.environ.get("FX_ORCHESTRATOR_AGENT", "")]
        record = {"backend": name, "name": name_on_server, "connection": connection}
        write_json(workspace / RECORD_NAME, record)
        session_id = backend.create(workspace, name_on_server, startup, background)
        write_json(workspace / RECORD_NAME, {**record, "id": session_id})
        return name, name_on_server, session_id
    finally:
        os.close(directory)


def close_terminal(workspace, task_name):
    try:
        directory = os.open(workspace, os.O_RDONLY | os.O_DIRECTORY)
    except FileNotFoundError:
        return close_workspace_session(workspace, task_name)
    try:
        fcntl.flock(directory, fcntl.LOCK_EX)
        return close_workspace_session(workspace, task_name)
    finally:
        os.close(directory)


def close_workspace_session(workspace, task_name):
    record = saved_terminal(workspace)
    if record:
        candidates = [(record["backend"], record["name"], record)]
    else:
        candidates = [(name, task_name, None) for name in BACKENDS]

    for name, label, saved in candidates:
        backend = BACKENDS[name]
        current = backend.current()
        if current and current in (label, (saved or {}).get("id")):
            raise ValueError(f"Run fx delete from a terminal outside {name.title()} session {label} so cleanup can finish.")
        session_id = find_saved(saved) if saved else backend.legacy_session(label, background=False)
        if not session_id:
            continue
        if current == session_id:
            raise ValueError(f"Run fx delete from a terminal outside {name.title()} session {label} so cleanup can finish.")
        backend.close(session_id)
        return True
    return False


def main():
    action, *arguments = sys.argv[1:]
    if action == "require":
        require_terminal()
    elif action == "group-mode":
        pane, _ = group_terminal()
        print("panes" if pane else "tabs")
    elif action == "tab":
        name, workspace, *arguments = arguments
        command, env = tab_command(name, Path(workspace), arguments)
        os.execvpe(command[0], command, env)
    elif action in ("open", "background", "close"):
        directory, task_name = arguments
        workspace = Path(directory)
        if action == "close":
            print("true" if close_terminal(workspace, task_name) else "false")
            return
        background = action == "background"
        name, label, session_id = ensure_terminal(workspace, task_name, background)
        backend = BACKENDS[name]
        if background:
            print(name, session_id, backend.hint(label, session_id), sep="\t")
        else:
            backend.show(workspace, label, session_id)
    else:
        raise ValueError(f"Unknown terminal action: {action}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        message = (error.stderr or "").strip()
        print(f"fx: Terminal command failed. {message or error}", file=sys.stderr)
        sys.exit(error.returncode)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        sys.exit(f"fx: {error}")
