import fcntl
import os
import pty
import select
import signal
import struct
import subprocess
import sys
import termios
import time


def client_count(session):
    result = subprocess.run(
        ["zellij", "--session", session, "action", "list-clients"],
        check=True, capture_output=True, text=True, timeout=5,
    )
    header, *clients = result.stdout.splitlines() or [""]
    if not header.startswith("CLIENT_ID "):
        raise RuntimeError(f"Could not read the client list for {session}.")
    return len(clients)


def run_tab_request(session, arguments):
    clients = client_count(session)
    pid, terminal = pty.fork()
    if pid == 0:
        try:
            fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 120, 0, 0))
            for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID"):
                os.environ.pop(key, None)
            os.environ["TERM"] = "xterm-256color"
            os.execlp("zellij", "zellij", "attach", session)
        finally:
            os._exit(1)

    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if not select.select([terminal], [], [], 0.1)[0]:
                continue
            if not os.read(terminal, 65536):
                break
            if client_count(session) > clients:
                return subprocess.run(
                    ["zellij", "--session", session, "action", "new-tab", *arguments],
                    timeout=15,
                ).returncode
        raise RuntimeError(f"The temporary Zellij client did not attach to {session}.")
    finally:
        os.close(terminal)
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        os.waitpid(pid, 0)


if __name__ == "__main__":
    try:
        sys.exit(run_tab_request(sys.argv[1], sys.argv[2:]))
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        sys.exit(f"fx: Could not open the Zellij tab: {error}")
