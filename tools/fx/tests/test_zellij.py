import json
from pathlib import Path
import shlex
import shutil
import subprocess
import time
import unittest
import uuid

import test_fx


ZELLIJ = shutil.which('zellij')


@unittest.skipUnless(ZELLIJ and shutil.which('script'), 'Zellij and script are required.')
class TaskOrchestratorTest(unittest.TestCase):
    def test_task_starts_orchestrator_and_can_restart_it_in_the_same_tab(self):
        fixture = test_fx.FxTest()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        name = 'fx-orchestrator-test-' + uuid.uuid4().hex[:12]
        project = Path(fixture.fx('setup', name, fixture.origin).stdout.strip())
        task = project / 'tasks/fix-login'
        session = f'{name}-fix-login'
        (fixture.bin / 'zellij').unlink()
        config = fixture.home / '.config/zellij'
        config.mkdir(parents=True)
        (config / 'config.kdl').write_text('show_startup_tips false\nshow_release_notes false\n')
        fixture.env.update(TERM='xterm-256color', SHELL='/bin/bash', FX_ORCHESTRATOR_AGENT='codex',
                           ZELLIJ_CONFIG_DIR=str(config), PATH=f"{test_fx.TOOL.parent}:{fixture.env['PATH']}")
        launches = fixture.root / 'orchestrator-launches.txt'
        shell_ready = fixture.root / 'shell-ready'
        (fixture.home / '.bashrc').write_text(f'touch -- {shlex.quote(str(shell_ready))}\n')
        (fixture.bin / 'codex').write_text(f'#!{test_fx.sys.executable}\n' + f'''
import os, sys
with open({str(launches)!r}, 'a') as log:
    print(os.getcwd(), os.environ['ZELLIJ_SESSION_NAME'], sys.stdin.isatty(), file=log)
try:
    input()
except KeyboardInterrupt:
    sys.exit(130)
''')
        self.addCleanup(fixture.run_command, ZELLIJ, 'delete-session', session, '--force', check=False)
        self.addCleanup(fixture.run_command, ZELLIJ, 'kill-session', session, check=False)

        def wait_for(predicate, message):
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if predicate():
                    return
                time.sleep(0.05)
            screen = fixture.run_command(ZELLIJ, '--session', session, 'action', 'dump-screen', '--full', check=False)
            self.fail(f'{message}\n{screen.stdout}')

        command = f'stty rows 40 cols 120; exec {shlex.quote(str(test_fx.TOOL))} task fix-login'
        with subprocess.Popen(
            ['script', '-qefc', command, '/dev/null'], cwd=project, env=fixture.env,
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        ) as client:
            try:
                wait_for(launches.exists, 'The orchestrator did not start.')
                tab_names = (ZELLIJ, '--session', session, 'action', 'query-tab-names')
                initial_tabs = fixture.run_command(*tab_names).stdout.splitlines()
                self.assertEqual(len(initial_tabs), 1)
                self.assertEqual(launches.read_text().splitlines(), [f'{task} {session} True'])
                client.stdin.write(b'\x03')
                client.stdin.flush()
                wait_for(shell_ready.exists, 'The task shell did not open after Ctrl+C.')
                client.stdin.write(b'fx orchestrator\r')
                client.stdin.flush()
                wait_for(lambda: len(launches.read_text().splitlines()) == 2,
                         'The orchestrator did not restart.')
                self.assertEqual(launches.read_text().splitlines(), [f'{task} {session} True'] * 2)
                self.assertEqual(fixture.run_command(*tab_names).stdout.splitlines(), initial_tabs)
                self.assertEqual(list((task / 'context').iterdir()), [])
            finally:
                client.terminate()
                client.wait(timeout=5)


@unittest.skipUnless(ZELLIJ and shutil.which('script'), 'Zellij and script are required.')
class ReviewAttachTest(unittest.TestCase):
    def test_background_review_survives_attach_and_accepts_input(self):
        fixture = test_fx.FxTest()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        project = fixture.project()
        fixture.review_repository(project / 'repo/main')
        (fixture.bin / 'zellij').unlink()
        fixture.env['TERM'] = 'xterm-256color'
        input_record = fixture.root / 'review-input.txt'
        (fixture.bin / 'claude').write_text(f'#!{test_fx.sys.executable}\n' + f"""
import sys
from pathlib import Path
if '--version' not in sys.argv:
    Path({str(input_record)!r}).write_text(input())
""")
        result = fixture.fx('pr', 'review', '17', cwd=project)
        session = result.stdout.split('zellij attach ')[-1].strip()
        self.addCleanup(fixture.run_command, ZELLIJ, 'delete-session', session, '--force', check=False)
        self.addCleanup(fixture.run_command, ZELLIJ, 'kill-session', session, check=False)

        def action(name):
            return fixture.run_command(ZELLIJ, '--session', session, 'action', name).stdout

        self.assertEqual(len(action('list-clients').splitlines()), 1)
        with subprocess.Popen(
            ['script', '-qefc', f'stty rows 40 cols 120; exec zellij attach {session}', '/dev/null'],
            env=fixture.env, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True,
        ) as client:
            try:
                deadline = time.monotonic() + 5
                while len(action('list-clients').splitlines()) < 2 and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertIn('000001-review-claude-opus-5-5', action('query-tab-names').splitlines())
                client.stdin.write(b'attach works\n')
                client.stdin.flush()
                deadline = time.monotonic() + 5
                while not input_record.exists() and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertTrue(input_record.exists(), 'The review did not receive terminal input.')
                self.assertEqual(input_record.read_text(), 'attach works')
            finally:
                client.terminate()
                client.wait(timeout=5)


@unittest.skipUnless(ZELLIJ, 'Zellij is required for terminal integration checks.')
class GroupTabTest(unittest.TestCase):
    def test_group_runs_and_starts_synthesis_when_session_template_has_a_command(self):
        fixture = test_fx.FxTest()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        task = fixture.task()
        fixture.batch_provider_stubs()
        marker = fixture.root / 'interactive-synthesis.json'
        template_marker = fixture.root / 'template-command.txt'
        claude = fixture.bin / 'claude'
        source = claude.read_text().replace(
            "session = Path(os.environ['FX_SESSION_CONTEXT_DIR'])",
            f'''if '--print' not in args:
    Path({str(marker)!r}).write_text(json.dumps({{'stdin_tty':sys.stdin.isatty(), 'cwd':os.getcwd()}}))
    time.sleep(60)
    sys.exit(0)
session = Path(os.environ['FX_SESSION_CONTEXT_DIR'])''')
        claude.write_text(source)
        (fixture.bin / 'zellij').unlink()
        (fixture.bin / 'zellij').symlink_to(ZELLIJ)
        fixture.env['SHELL'] = '/bin/bash'
        name = 'fx-group-test-' + uuid.uuid4().hex[:12]
        template_command = (
            f'from pathlib import Path; import time; Path({str(template_marker)!r}).write_text("started"); time.sleep(60)')
        layout = f'''layout {{
    new_tab_template {{
        pane command="python3" {{
            args "-c" {json.dumps(template_command)}
        }}
    }}
    pane
}}
'''
        fixture.run_command(ZELLIJ, '--layout-string', layout, 'attach', '--create-background', name)
        def close_session():
            fixture.run_command(ZELLIJ, 'kill-session', name, check=False)
            fixture.run_command(ZELLIJ, 'delete-session', name, check=False)
        self.addCleanup(close_session)
        fixture.env.update(ZELLIJ='0', ZELLIJ_SESSION_NAME=name)
        before = fixture.run_command(ZELLIJ, '--session', name, 'action', 'query-tab-names').stdout.splitlines()
        fixture.fx('agent', 'group', '--name', 'review', '--agent', 'claude', '--agent', 'codex',
                   '--prompt', 'Review source', cwd=task)
        deadline = time.monotonic() + 10
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        state_path, = (task / 'context/groups').glob('*/run-state.json')
        state = json.loads(state_path.read_text())
        self.assertTrue(marker.exists(), f'Interactive synthesis did not start; template ran: {template_marker.exists()}; group state: {state}')
        self.assertEqual(state['status'], 'finished')
        result = json.loads(marker.read_text())
        self.assertTrue(result['stdin_tty'])
        self.assertEqual(result['cwd'], str(task))
        after = fixture.run_command(ZELLIJ, '--session', name, 'action', 'query-tab-names').stdout.splitlines()
        self.assertEqual(len(after), len(before) + 1)
        self.assertEqual(after[-1], '000001-review')

    def check_interactive_launch(self, mode):
        fixture = test_fx.FxTest()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        task = fixture.task()
        if mode == 'compare':
            group = fixture.completed_group(task)
            arguments = ('agent', 'group', 'compare', group.name, '--name', 'summary', '--new-tab')
        else:
            arguments = ('agent', 'codex', '--name', 'review', '--prompt', 'Review source', '--new-tab')
        marker = fixture.root / 'interactive.json'
        (fixture.bin / ('claude' if mode == 'compare' else 'codex')).write_text(f'#!{test_fx.sys.executable}\n' + f'''import json, os, sys, time
from pathlib import Path
if '--version' in sys.argv:
    print('test version')
    sys.exit(0)
Path({str(marker)!r}).write_text(json.dumps({{'stdin_tty':sys.stdin.isatty(), 'cwd':os.getcwd()}}))
time.sleep(60)
''')
        (fixture.bin / 'zellij').unlink()
        (fixture.bin / 'zellij').symlink_to(ZELLIJ)
        fixture.env['SHELL'] = '/bin/bash'
        name = 'fx-agent-tab-test-' + uuid.uuid4().hex[:12]
        layout = 'layout { new_tab_template { pane command="/bin/sleep" { args "60"; }; }; pane; }'
        fixture.env.pop('ZELLIJ', None)
        fixture.env.pop('ZELLIJ_SESSION_NAME', None)
        fixture.run_command(ZELLIJ, '--layout-string', layout, 'attach', '--create-background', name)
        def close_session():
            fixture.run_command(ZELLIJ, 'kill-session', name, check=False)
            fixture.run_command(ZELLIJ, 'delete-session', name, check=False)
        self.addCleanup(close_session)
        fixture.env.update(ZELLIJ='0', ZELLIJ_SESSION_NAME=name)
        before = fixture.run_command(ZELLIJ, '--session', name, 'action', 'query-tab-names').stdout.splitlines()
        fixture.fx(*arguments, cwd=task)
        deadline = time.monotonic() + 5
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertTrue(marker.exists(), f'{mode} ran the session template instead of the agent')
        result = json.loads(marker.read_text())
        self.assertTrue(result['stdin_tty'])
        self.assertEqual(result['cwd'], str(task))
        after = fixture.run_command(ZELLIJ, '--session', name, 'action', 'query-tab-names').stdout.splitlines()
        self.assertEqual(len(after), len(before) + 1)

    def test_individual_agent_new_tab_overrides_the_session_command(self):
        self.check_interactive_launch('agent')

    def test_group_comparison_new_tab_overrides_the_session_command(self):
        self.check_interactive_launch('compare')


if __name__ == '__main__':
    unittest.main()
