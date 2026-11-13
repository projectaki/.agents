import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from fx_terminal import tab_command
from fx_usage import write_json


TOOL_DIR = Path(__file__).resolve().parent


class TabProcess:
    def __init__(self, project, task, group, member, log, open_pane=None):
        self.session = group / member['session']
        self.record = self.session / 'terminal-state.json'
        self.cancelled = self.session / 'terminal-cancelled'
        arguments = [sys.executable, str(Path(__file__).resolve()), str(project), str(task),
                     str(self.session), member['agent'], member['reasoning']]
        try:
            if open_pane:
                open_pane(arguments, log)
            else:
                command, env = tab_command(f"{group.name}-{member['session']}", task, arguments)
                request = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=40)
                if request.returncode:
                    raise OSError(f'Terminal tab request failed with exit code {request.returncode}.')
            deadline = time.monotonic() + 15
            while not self.record.exists():
                if time.monotonic() >= deadline:
                    raise OSError('The member tab did not report startup within 15 seconds.')
                time.sleep(0.05)
            state = json.loads(self.record.read_text())
            self.pid = state['pid']
            if not state['isolated']:
                raise OSError('The member tab must have its own process group.')
        except BaseException as error:
            self.cancelled.touch()
            if self.record.exists():
                state = json.loads(self.record.read_text())
                if state['isolated'] and 'exit_code' not in state:
                    try:
                        os.killpg(state['pid'], signal.SIGTERM)
                    except ProcessLookupError:
                        pass
            if isinstance(error, subprocess.TimeoutExpired):
                raise OSError('The terminal tab request timed out.') from error
            if isinstance(error, ValueError):
                raise OSError(str(error)) from error
            raise

    def poll(self):
        state = json.loads(self.record.read_text())
        if 'exit_code' in state:
            return state['exit_code']
        try:
            os.kill(self.pid, 0)
        except ProcessLookupError:
            return 1
        return None

    def wait(self, timeout=None):
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            code = self.poll()
            if code is not None:
                return code
            if deadline is not None and time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired('interactive member', timeout)
            time.sleep(0.05)


def run_member(project, task, session, agent, reasoning):
    state = {'pid': os.getpid(), 'isolated': os.getpgrp() == os.getpid()}
    record = session / 'terminal-state.json'

    def cancel(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, lambda signum, frame: None)
    for signum in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, cancel)
    process = None
    code = 1
    try:
        write_json(record, state)
        if not state['isolated'] or (session / 'terminal-cancelled').exists():
            return 1
        command = [str(TOOL_DIR / 'agents' / agent), 'launch', str(project), str(task),
                   str(session), reasoning, (session / 'initial_prompt.md').read_text()]
        process = subprocess.Popen(command, cwd=task)
        code = process.wait()
    except KeyboardInterrupt:
        code = 130
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(signum, signal.SIG_IGN)
        os.killpg(os.getpgrp(), signal.SIGTERM)
        if process is not None:
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    except OSError as error:
        print(f'fx: Cannot start interactive member: {error}', file=sys.stderr)
    finally:
        write_json(record, {**state, 'exit_code': code})
    return code


class GroupPanes:
    def __init__(self, create_pane, session_id, workspace, group_name):
        self.create_pane = create_pane
        self.session_id = session_id
        self.workspace = workspace
        self.group_name = group_name
        self.anchor = None
        self.creation_failed = False

    def open(self, member, remaining, arguments, log):
        if self.creation_failed:
            raise OSError("A previous pane request failed. Check the group tab before retrying.")
        try:
            result = self.create_pane(self.session_id, self.workspace, self.group_name,
                                      member, arguments, self.anchor, remaining)
            print(json.dumps(result), file=log, flush=True)
            self.anchor = result["block_ids"][0]
        except subprocess.CalledProcessError as error:
            self.creation_failed = True
            raise OSError(error.stderr.strip() or str(error)) from error
        except (OSError, ValueError, KeyError, IndexError, subprocess.TimeoutExpired) as error:
            self.creation_failed = True
            raise OSError(f"Cannot create group pane: {error}") from error


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('project', type=Path)
    parser.add_argument('task', type=Path)
    parser.add_argument('session', type=Path)
    parser.add_argument('agent')
    parser.add_argument('reasoning')
    args = parser.parse_args()
    sys.exit(run_member(args.project, args.task, args.session, args.agent, args.reasoning))
