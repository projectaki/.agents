import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fx_context import group_sessions, save_response
from fx_group_run import prepare_run, retry_members, write_json


class GroupRunTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.group = Path(temporary.name) / 'context/groups/000001-review'
        self.group.mkdir(parents=True)
        self.first = self.group / '1-agent-model'
        self.first.mkdir()
        (self.first / 'launch.txt').write_text('agent=agent\nreasoning=high\n')
        (self.first / 'instructions.md').write_text(f'Write to {self.first}/findings.md')
        (self.first / 'handoff.md').write_text(f'Session: {self.first}')
        (self.first / 'input-context.md').write_text('Starting context')
        (self.first / 'initial_prompt.md').write_text(f'Keep this literal: {self.first}')
        (self.group / 'group.md').write_text(f'| {self.first.name} | agent | high |')
        prepare_run(self.group, 'synthesis-agent')
        self.manifest = json.loads((self.group / 'run.json').read_text())
        self.state = json.loads((self.group / 'run-state.json').read_text())

    def test_prepare_records_members_provider_reasoning_and_waiting_state(self):
        self.assertEqual(self.manifest['synthesis_agent'], 'synthesis-agent')
        self.assertEqual(self.manifest['members'], [
            {'session': self.first.name, 'agent': 'agent', 'reasoning': 'high'}])
        self.assertEqual(self.state['members'][self.first.name]['status'], 'waiting')

    def test_manifest_selects_active_members_and_rejects_invalid_paths(self):
        extra = self.group / 'unused-attempt'
        extra.mkdir()
        (extra / 'instructions.md').write_text('Previous attempt')
        self.assertEqual(group_sessions(self.group), [self.first])
        for name in ('../outside', '.', '', 'nested/member'):
            with self.subTest(name=name):
                self.manifest['members'][0]['session'] = name
                write_json(self.group / 'run.json', self.manifest)
                with self.assertRaises(ValueError):
                    group_sessions(self.group)

    def test_manifest_rejects_duplicate_members_and_symbolic_links(self):
        self.manifest['members'] *= 2
        write_json(self.group / 'run.json', self.manifest)
        with self.assertRaisesRegex(ValueError, 'distinct'):
            group_sessions(self.group)
        (self.group / 'run.json').unlink()
        outside = self.group / 'other.json'
        outside.write_text(json.dumps(self.manifest))
        (self.group / 'run.json').symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'symbolic link'):
            group_sessions(self.group)

    def test_retry_preserves_original_assignment_and_replaces_private_paths(self):
        (self.first / 'model.txt').write_text('z-ai/glm-5.3\n')
        retry_members(self.group, self.manifest, self.state)
        retry = group_sessions(self.group)[0]
        self.assertNotEqual(retry, self.first)
        self.assertEqual((retry / 'initial_prompt.md').read_text(), (self.first / 'initial_prompt.md').read_text())
        self.assertEqual((retry / 'input-context.md').read_text(), 'Starting context')
        self.assertIn(str(retry / 'findings.md'), (retry / 'instructions.md').read_text())
        self.assertIn(str(retry), (retry / 'handoff.md').read_text())
        self.assertIn(retry.name, (self.group / 'group.md').read_text())
        self.assertTrue(self.first.exists())
        self.assertEqual((retry / 'model.txt').read_text(), 'z-ai/glm-5.3\n')

    def test_retry_rejects_completed_group_but_recovers_missing_result(self):
        result = save_response(self.first, 'agent', 'conversation', 'turn', 'Report')
        self.state['members'][self.first.name]['status'] = 'finished'
        with self.assertRaisesRegex(ValueError, 'All members finished'):
            retry_members(self.group, self.manifest, self.state)
        (result / 'response.md').unlink()
        retry_members(self.group, self.manifest, self.state)
        self.assertNotEqual(group_sessions(self.group)[0], self.first)


if __name__ == '__main__':
    unittest.main()
