import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'agents'))
import claude_usage
import codex_usage
import fx_group_run
from fx_usage import (TOKEN_FIELDS, collect_usage, group_usage, render_group_usage,
                      unavailable_usage, validate_usage, write_json)


class UsageTest(unittest.TestCase):
    def claude_result(self, **changes):
        return {'subtype': 'success', 'total_cost_usd': 0.123,
                'usage': {'input_tokens': 10, 'cache_read_input_tokens': 20,
                          'cache_creation_input_tokens': 30, 'output_tokens': 40}, **changes}

    def codex_events(self, *records):
        return [json.dumps(record) for record in records]

    def turn(self, **usage):
        return {'type': 'turn.completed', 'usage': {
            'input_tokens': 100, 'cached_input_tokens': 60,
            'output_tokens': 20, 'reasoning_output_tokens': 10, **usage}}

    def test_claude_normalizes_disjoint_input_categories_without_double_counting_cost(self):
        usage = claude_usage.result_usage(self.claude_result())
        self.assertEqual(usage['input_tokens'], 60)
        self.assertEqual(usage['output_tokens'], 40)
        self.assertEqual(usage['cached_input_tokens'], 20)
        self.assertEqual(usage['cache_write_input_tokens'], 30)
        self.assertEqual(usage['cost_usd'], 0.123)
        self.assertEqual(usage['cost_kind'], 'estimated')
        self.assertEqual(usage['coverage'], 'partial')
        self.assertIn('Main agent only', usage['token_scope'])

    def test_claude_prefers_model_totals_including_subagents(self):
        models = {
            'main': {'inputTokens': 10, 'cacheReadInputTokens': 20, 'cacheCreationInputTokens': 30, 'outputTokens': 40},
            'child': {'inputTokens': 1, 'cacheReadInputTokens': 2, 'cacheCreationInputTokens': 3, 'outputTokens': 4},
        }
        for key in ('modelUsage', 'model_usage'):
            with self.subTest(key=key):
                usage = claude_usage.result_usage(self.claude_result(**{key: models}))
                self.assertEqual(usage['input_tokens'], 66)
                self.assertEqual(usage['output_tokens'], 44)
                self.assertEqual(usage['cost_usd'], 0.123)
                self.assertEqual(usage['coverage'], 'complete')

    def test_claude_error_result_preserves_known_usage_and_missing_counts_stay_unknown(self):
        usage = claude_usage.result_usage(self.claude_result(subtype='error_max_turns', total_cost_usd=0))
        self.assertEqual(usage['coverage'], 'partial')
        self.assertEqual(usage['cost_usd'], 0)
        missing = claude_usage.result_usage({'total_cost_usd': 0.5})
        self.assertIsNone(missing['input_tokens'])
        self.assertIsNone(missing['output_tokens'])
        self.assertEqual(missing['cost_usd'], 0.5)
        with self.assertRaises(ValueError):
            claude_usage.result_usage(self.claude_result(usage={'input_tokens': -1}))

    def test_codex_sums_completed_turns_and_preserves_cached_and_reasoning_subsets(self):
        usage = codex_usage.event_usage(self.codex_events(self.turn(), self.turn()))
        self.assertEqual(usage['input_tokens'], 200)
        self.assertEqual(usage['cached_input_tokens'], 120)
        self.assertEqual(usage['output_tokens'], 40)
        self.assertEqual(usage['reasoning_output_tokens'], 20)
        self.assertIsNone(usage['cost_usd'])
        self.assertEqual(usage['cost_kind'], 'unavailable')
        self.assertEqual(usage['coverage'], 'complete')

    def test_codex_partial_events_keep_completed_usage_and_do_not_claim_zero(self):
        for tail in ('{"type":', json.dumps({'type': 'turn.failed'}),
                     json.dumps({'type': 'turn.completed'})):
            with self.subTest(tail=tail):
                usage = codex_usage.event_usage([json.dumps(self.turn()), tail])
                self.assertEqual(usage['input_tokens'], 100)
                self.assertEqual(usage['coverage'], 'partial')
        for lines in ([], ['not json'], [json.dumps({'type': 'turn.completed'})]):
            usage = codex_usage.event_usage(lines)
            self.assertIsNone(usage['input_tokens'])
            self.assertIsNone(usage['cost_usd'])
        usage = codex_usage.event_usage(self.codex_events(self.turn(), self.turn(input_tokens=None)))
        self.assertIsNone(usage['input_tokens'])
        self.assertEqual(usage['output_tokens'], 40)
        self.assertEqual(usage['coverage'], 'partial')

    def test_cost_estimate_subtracts_cache_hits_and_does_not_add_reasoning_twice(self):
        pricing = {'prompt': '0.01', 'completion': '0.02', 'input_cache_read': '0.001'}
        usage = codex_usage.event_usage(self.codex_events(self.turn()), pricing)
        self.assertAlmostEqual(usage['cost_usd'], 0.86)
        self.assertEqual(usage['cost_kind'], 'estimated')
        reported = codex_usage.event_usage(self.codex_events(self.turn(cost=0)), pricing)
        self.assertEqual(reported['cost_usd'], 0)
        self.assertEqual(reported['cost_kind'], 'reported')
        for change in ({'prompt': 'NaN'}, {'completion': '-1'}, {'input_cache_read': None}):
            with self.subTest(change=change):
                self.assertIsNone(codex_usage.estimate_cost(usage, {**pricing, **change}))
        self.assertIsNone(codex_usage.estimate_cost({**usage, 'cached_input_tokens': None}, pricing))

    def test_usage_validation_rejects_invalid_numbers_and_inconsistent_subsets(self):
        base = unavailable_usage('Unknown')
        for change in ({'input_tokens': True}, {'output_tokens': 1.2}, {'input_tokens': -1},
                       {'cost_usd': float('nan'), 'cost_kind': 'estimated'},
                       {'cost_usd': float('inf'), 'cost_kind': 'estimated'},
                       {'cost_usd': -1, 'cost_kind': 'estimated'}, {'cost_kind': 'reported'},
                       {'input_tokens': 1, 'cached_input_tokens': 2},
                       {'output_tokens': 1, 'reasoning_output_tokens': 2}, {'notes': 'invalid'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_usage({**base, **change})


class UsageFilesTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.session = self.root / 'context/groups/000001-review/1-custom-model'
        self.session.mkdir(parents=True)
        self.group = self.session.parent
        self.tool = self.root / 'tool'
        (self.tool / 'agents').mkdir(parents=True)
        (self.session / 'launch.txt').write_text('agent=custom\nmodel=example/model\nreasoning=high\n')
        (self.session / 'instructions.md').write_text('Investigate')
        (self.session / 'initial_prompt.md').write_text('Review')
        self.manifest = {'members': [{'session': self.session.name, 'agent': 'custom', 'reasoning': 'high'}]}
        self.state = {'status': 'waiting', 'members': {self.session.name: {'status': 'waiting'}}}

    def test_collect_uses_registered_adapter_and_reports_missing_or_invalid_usage(self):
        usage = unavailable_usage('Not measured')
        self.assertEqual(collect_usage(self.tool, self.session, 'missing')['coverage'], 'unavailable')
        adapter = self.tool / 'agents/custom.usage'
        adapter.write_text(f'#!{sys.executable}\nimport json\nprint({json.dumps(usage)!r})\n')
        adapter.chmod(0o755)
        self.assertEqual(collect_usage(self.tool, self.session, 'custom'), usage)
        adapter.write_text(f'#!{sys.executable}\nprint("not JSON")\n')
        self.assertEqual(collect_usage(self.tool, self.session, 'custom')['coverage'], 'unavailable')
        adapter.write_text(f'#!{sys.executable}\nraise SystemExit(23)\n')
        self.assertIn('23', collect_usage(self.tool, self.session, 'custom')['notes'][0])

    def test_group_runner_saves_runtime_and_report_without_provider_branches(self):
        adapter = self.tool / 'agents/custom.batch'
        adapter.write_text(f'#!{sys.executable}\n')
        adapter.chmod(0o755)
        with patch.object(fx_group_run, 'TOOL_DIR', self.tool), \
             patch.object(fx_group_run, 'captured_results', return_value=[True]), \
             patch('sys.stdout', new_callable=io.StringIO) as output:
            fx_group_run.run_members(self.root, self.root, self.group, self.manifest, self.state)
        attempt = self.state['members'][self.session.name]
        self.assertEqual(attempt['status'], 'finished')
        self.assertGreater(attempt['runtime_seconds'], 0)
        self.assertIn('started_at', attempt)
        self.assertIn('finished_at', attempt)
        report = json.loads((self.group / 'usage-summary.json').read_text())
        self.assertEqual(report['attempts'][0]['model'], 'example/model')
        self.assertEqual(report['attempts'][0]['usage']['coverage'], 'unavailable')
        self.assertGreater(report['wall_seconds'], 0)
        self.assertTrue((self.session / 'usage.json').exists())
        self.assertIn('Cost USD', output.getvalue())
        self.assertIn('unavailable', (self.group / 'usage-summary.md').read_text())

    def test_reports_keep_failed_attempts_after_retry_and_do_not_sum_parallel_runtime(self):
        usage = unavailable_usage('Unreported')
        write_json(self.session / 'usage.json', usage)
        retry = self.group / (self.session.name + '-retry-2')
        retry.mkdir()
        (retry / 'launch.txt').write_text((self.session / 'launch.txt').read_text())
        write_json(retry / 'usage.json', usage)
        self.state['members'][self.session.name] = {'status': 'failed', 'runtime_seconds': 5}
        self.state['members'][retry.name] = {'status': 'finished', 'runtime_seconds': 7}
        self.state['wall_seconds'] = 8
        self.manifest['members'][0]['session'] = retry.name
        report = group_usage(self.group, self.manifest, self.state)
        self.assertEqual([attempt['active'] for attempt in report['attempts']], [False, True])
        self.assertEqual([attempt['status'] for attempt in report['attempts']], ['failed', 'finished'])
        self.assertEqual(report['wall_seconds'], 8)
        self.assertIn('8.00s', render_group_usage(report))
        self.assertNotIn('$0.000000', render_group_usage(report))

    def test_failed_attempt_retains_known_usage_as_partial_and_start_failure_has_runtime(self):
        adapter = self.tool / 'agents/custom.batch'
        adapter.write_text(f'#!{sys.executable}\nraise SystemExit(23)\n')
        adapter.chmod(0o755)
        usage = codex_usage.event_usage([json.dumps({'type': 'turn.completed', 'usage': {
            'input_tokens': 100, 'cached_input_tokens': 0, 'output_tokens': 20}})])
        with patch.object(fx_group_run, 'TOOL_DIR', self.tool), \
             patch.object(fx_group_run, 'collect_usage', return_value=usage), \
             patch('sys.stdout', new_callable=io.StringIO):
            fx_group_run.run_members(self.root, self.root, self.group, self.manifest, self.state)
        saved = json.loads((self.session / 'usage.json').read_text())
        self.assertEqual(self.state['status'], 'failed')
        self.assertEqual(saved['input_tokens'], 100)
        self.assertEqual(saved['coverage'], 'partial')
        (self.session / 'runner.log').unlink()
        adapter.unlink()
        self.state['members'][self.session.name] = {'status': 'waiting'}
        with patch.object(fx_group_run, 'TOOL_DIR', self.tool), \
             patch('sys.stdout', new_callable=io.StringIO):
            fx_group_run.run_members(self.root, self.root, self.group, self.manifest, self.state)
        self.assertEqual(self.state['members'][self.session.name]['status'], 'failed')
        self.assertGreaterEqual(self.state['members'][self.session.name]['runtime_seconds'], 0)

    def test_registered_usage_adapters_read_preserved_events_without_network(self):
        tool = Path(__file__).resolve().parents[1]
        events = self.session / 'events'
        events.mkdir()
        (events / 'codex-exec.jsonl').write_text(json.dumps({'type': 'turn.completed', 'usage': {
            'input_tokens': 100, 'cached_input_tokens': 20, 'output_tokens': 10}}) + '\n')
        for agent in ('codex', 'deepseek', 'glm', 'minimax', 'gemini'):
            with self.subTest(agent=agent):
                self.assertEqual(collect_usage(tool, self.session, agent)['input_tokens'], 100)
        (events / 'claude-result.json').write_text(json.dumps({
            'subtype': 'success', 'total_cost_usd': 0.1,
            'usage': {'input_tokens': 10, 'cache_read_input_tokens': 20,
                      'cache_creation_input_tokens': 30, 'output_tokens': 40}}))
        self.assertEqual(collect_usage(tool, self.session, 'claude')['input_tokens'], 60)

    def test_unreadable_pricing_does_not_discard_token_usage(self):
        events = self.session / 'events'
        events.mkdir()
        (events / 'codex-exec.jsonl').write_text(json.dumps({'type': 'turn.completed', 'usage': {
            'input_tokens': 100, 'cached_input_tokens': 20, 'output_tokens': 10}}) + '\n')
        for text in ('not JSON', '[]', '{}', '{"pricing": null}'):
            with self.subTest(text=text):
                (self.session / 'pricing.json').write_text(text)
                usage = collect_usage(Path(__file__).resolve().parents[1], self.session, 'glm')
                self.assertEqual(usage['input_tokens'], 100)
                self.assertIsNone(usage['cost_usd'])
                self.assertIn('Pricing snapshot', ' '.join(usage['notes']))

    def test_bad_usage_sidecar_is_unavailable_and_symbolic_links_are_rejected(self):
        (self.session / 'usage.json').write_text('not json')
        report = group_usage(self.group, self.manifest, self.state)
        self.assertEqual(report['attempts'][0]['usage']['coverage'], 'unavailable')
        self.state['members']['../outside'] = {'status': 'finished'}
        with self.assertRaises(ValueError):
            group_usage(self.group, self.manifest, self.state)


if __name__ == '__main__':
    unittest.main()
