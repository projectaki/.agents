import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import time
import unittest
import uuid
from unittest.mock import patch

import test_fx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fx_group_tabs import TabProcess
from fx_group_run import prepare_run, run_members
import test_group_run


class TabProcessTest(unittest.TestCase):
    setUp = test_group_run.GroupRunTest.setUp
    def test_prepare_saves_interactive_mode_for_retry(self):
        prepare_run(self.group, 'synthesis-agent', interactive=True)
        self.assertTrue(json.loads((self.group / 'run.json').read_text())['interactive'])

    def test_interrupt_during_tab_startup_records_cancelled_member(self):
        self.manifest['interactive'] = True
        with patch('fx_group_run.TabProcess', side_effect=KeyboardInterrupt):
            with patch('fx_group_run.collect_usage', return_value={'coverage': 'unavailable'}):
                with patch('fx_group_run.save_group_usage'):
                    with self.assertRaises(KeyboardInterrupt):
                        run_members(self.group, self.group, self.group, self.manifest, self.state)
        self.assertEqual(self.state['status'], 'failed')
        self.assertEqual(self.state['members'][self.first.name]['status'], 'cancelled')

    def test_startup_timeout_cancels_a_late_member(self):
        member = self.manifest['members'][0]
        with (self.first / 'runner.log').open('w') as log:
            with patch.dict(os.environ, ZELLIJ='0', ZELLIJ_SESSION_NAME='test'):
                with patch('fx_group_tabs.subprocess.run') as request:
                    request.return_value.returncode = 0
                    with patch('fx_group_tabs.time.monotonic', side_effect=[0, 15]):
                        with self.assertRaisesRegex(OSError, 'report startup'):
                            TabProcess(self.group, self.group, self.group, member, log)
        self.assertTrue((self.first / 'terminal-cancelled').exists())

    def test_poll_requires_exit_even_after_a_response_exists(self):
        process = TabProcess.__new__(TabProcess)
        process.record = self.first / 'terminal-state.json'
        process.pid = os.getpid()
        process.record.write_text(json.dumps({'pid': process.pid}))
        (self.first / 'last_turn_results.md').write_text('Saved response')
        self.assertIsNone(process.poll())
        process.record.write_text(json.dumps({'pid': process.pid, 'exit_code': 23}))
        self.assertEqual(process.wait(timeout=0), 23)

    def test_poll_detects_member_killed_without_an_exit_record(self):
        process = TabProcess.__new__(TabProcess)
        process.record = self.first / 'terminal-state.json'
        process.pid = 12345
        process.record.write_text('{}')
        with patch('fx_group_tabs.os.kill', side_effect=ProcessLookupError):
            self.assertEqual(process.poll(), 1)

    def test_tab_failure_preserves_request_log_and_cancels_late_start(self):
        member = self.manifest['members'][0]
        with (self.first / 'runner.log').open('w') as log:
            with patch.dict(os.environ, ZELLIJ='0', ZELLIJ_SESSION_NAME='test'):
                with patch('fx_group_tabs.subprocess.run') as request:
                    request.return_value.returncode = 23
                    with self.assertRaisesRegex(OSError, 'exit code 23'):
                        TabProcess(self.group, self.group, self.group, member, log)
        self.assertTrue((self.first / 'terminal-cancelled').exists())


ZELLIJ = shutil.which('zellij')


@unittest.skipUnless(ZELLIJ, 'Zellij is required for terminal integration checks.')
class InteractiveGroupTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture = test_fx.FxTest()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.task = fixture.task()
        self.marker = fixture.root / 'synthesis.json'
        self.release = fixture.root / 'release'
        self.failure_marker = fixture.root / 'fail'
        self.empty = fixture.root / 'empty'
        script = f'#!{sys.executable}\n' + f'''import json, os, signal, sys, time
from pathlib import Path
sys.path.insert(0, {str(test_fx.TOOL.parent)!r})
from fx_context import save_response
args = sys.argv[1:]
if '--version' in args:
    print('test version')
    sys.exit(0)
assert '--print' not in args and 'exec' not in args
session = Path(args[args.index('--settings') + 1]).parent if '--settings' in args else Path(os.environ['FX_SESSION_CONTEXT_DIR'])
assert sys.stdin.isatty()
os.close(os.open('/dev/tty', os.O_RDWR))
if session.parent.name == 'comparisons':
    Path({str(self.marker)!r}).write_text(json.dumps({{'tty': sys.stdin.isatty(), 'session': str(session)}}))
    time.sleep(60)
    sys.exit(0)
if not Path({str(self.empty)!r}).exists():
    save_response(session, 'test', session.name, 'one', 'Report from ' + session.name)
signal.signal(signal.SIGINT, lambda signum, frame: (session / 'interrupted').write_text('interrupted'))
(session / 'started').write_text('started')
while not Path({str(self.release)!r}).exists() and not (session / 'release').exists():
    time.sleep(0.02)
sys.exit(23 if Path({str(self.failure_marker)!r}).exists() else 0)
'''
        for agent in ('claude', 'codex'):
            (fixture.bin / agent).write_text(script)
        (fixture.bin / 'zellij').unlink()
        (fixture.bin / 'zellij').symlink_to(ZELLIJ)
        fixture.env['SHELL'] = '/bin/bash'
        self.name = 'fx-interactive-test-' + uuid.uuid4().hex[:12]
        fixture.run_command(ZELLIJ, 'attach', '--create-background', self.name)
        self.addCleanup(self.close_session)
        fixture.env.update(ZELLIJ='0', ZELLIJ_SESSION_NAME=self.name)
        fixture.fx('agent', 'group', '--interactive', '--name', 'review', '--agent', 'claude',
                   '--agent', 'codex', '--prompt', 'Review source', cwd=self.task)
        self.group, = (self.task / 'context/groups').iterdir()
        self.members = [self.group / m['session'] for m in json.loads((self.group / 'run.json').read_text())['members']]
        self.until(lambda: all((member / 'started').exists() for member in self.members))

    def close_session(self):
        self.fixture.run_command(ZELLIJ, 'kill-session', self.name, check=False)
        self.fixture.run_command(ZELLIJ, 'delete-session', self.name, check=False)

    def until(self, predicate):
        deadline = time.monotonic() + 15
        while not predicate():
            if time.monotonic() >= deadline:
                self.fail_test()
            time.sleep(0.05)

    def fail_test(self):
        state = (self.task / 'context/groups/000001-review/run-state.json').read_text()
        self.fail(f'Group did not reach expected state: {state}')

    def stopped(self):
        with (self.group / '.run.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except BlockingIOError:
                return False

    def state(self):
        return json.loads((self.group / 'run-state.json').read_text())

    def start_synthesis(self, check=True):
        return self.fixture.fx('agent', 'group', 'compare', self.group.name,
                               '--name', 'synthesis', '--new-tab', cwd=self.task, check=check)

    def test_successful_member_exits_do_not_start_synthesis(self):
        self.release.touch()
        self.until(lambda: self.state()['status'] == 'finished')
        self.until(self.stopped)
        self.assertFalse(self.marker.exists())
        self.assertFalse((self.group / 'comparisons').exists())

    def test_manual_synthesis_requires_a_response_from_every_member(self):
        shutil.rmtree(self.members[0] / 'results')
        (self.members[0] / 'last_turn_results.md').unlink()
        result = self.start_synthesis(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('No captured responses', result.stderr)
        self.assertFalse(self.marker.exists())

    def test_manual_synthesis_uses_saved_responses_while_members_stay_open(self):
        self.assertFalse(self.marker.exists())
        self.start_synthesis()
        self.until(self.marker.exists)
        self.assertEqual(self.state()['status'], 'running')
        for member in self.members:
            terminal = json.loads((member / 'terminal-state.json').read_text())
            self.assertNotIn('exit_code', terminal)
            os.kill(terminal['pid'], 0)
        tabs = self.fixture.run_command(ZELLIJ, '--session', self.name, 'action', 'query-tab-names').stdout.splitlines()
        for member in self.members:
            self.assertIn(f'{self.group.name}-{member.name}', tabs)
        synthesis = Path(json.loads(self.marker.read_text())['session'])
        self.assertEqual(tabs[-1], synthesis.name)
        self.assertEqual(synthesis.parent, self.group / 'comparisons')

    def test_failure_blocks_synthesis_and_retry_keeps_interactive_mode(self):
        self.failure_marker.touch()
        self.release.touch()
        self.until(lambda: self.state()['status'] == 'failed')
        self.assertFalse(self.marker.exists())
        self.failure_marker.unlink()
        self.until(self.stopped)
        retried = self.fixture.fx('agent', 'group', 'retry', self.group.name, cwd=self.task, check=False)
        self.assertEqual(retried.returncode, 0, retried.stderr)
        self.assertFalse(self.marker.exists())
        self.start_synthesis()
        self.until(self.marker.exists)
        manifest = json.loads((self.group / 'run.json').read_text())
        self.assertTrue(manifest['interactive'])
        self.assertTrue(all('-retry-' in m['session'] for m in manifest['members']))

    def test_zero_exit_without_response_blocks_synthesis(self):
        for member in self.members:
            shutil.rmtree(member / 'results')
            (member / 'last_turn_results.md').unlink()
        self.release.touch()
        self.until(lambda: self.state()['status'] == 'failed')
        self.assertFalse(self.marker.exists())

    def test_member_interrupt_preserves_interactive_provider_control(self):
        terminal = json.loads((self.members[0] / 'terminal-state.json').read_text())
        os.killpg(terminal['pid'], signal.SIGINT)
        self.until(lambda: (self.members[0] / 'interrupted').exists())
        self.assertNotIn('exit_code', json.loads((self.members[0] / 'terminal-state.json').read_text()))
        self.assertFalse(self.marker.exists())
        self.start_synthesis()
        self.until(self.marker.exists)

    def test_interrupt_stops_member_process_groups(self):
        self.until(lambda: 'runner_pid' in self.state())
        os.kill(self.state()['runner_pid'], signal.SIGINT)
        self.until(lambda: self.state()['status'] == 'failed')
        self.until(self.stopped)
        self.assertFalse(self.marker.exists())
        self.assertTrue(all(m['status'] == 'cancelled' for m in self.state()['members'].values()))
        for member in self.members:
            pid = json.loads((member / 'terminal-state.json').read_text())['pid']
            with self.assertRaises(ProcessLookupError):
                os.killpg(pid, 0)

    def test_killed_member_blocks_synthesis(self):
        terminal = json.loads((self.members[0] / 'terminal-state.json').read_text())
        os.killpg(terminal['pid'], signal.SIGKILL)
        self.release.touch()
        self.until(lambda: self.state()['status'] == 'failed')
        self.assertFalse(self.marker.exists())


if __name__ == '__main__':
    unittest.main()
