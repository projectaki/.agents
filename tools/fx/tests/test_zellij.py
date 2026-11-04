import json
from pathlib import Path
import shutil
import time
import unittest
import uuid

import test_fx


ZELLIJ = shutil.which('zellij')


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
