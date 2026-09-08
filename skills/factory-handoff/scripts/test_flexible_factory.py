from __future__ import annotations

import json
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from prerequisites import plan_fingerprint, prerequisite_errors
from records import validate_acceptance, validate_root
from routing import decide
from test_records import assurance, implementation_history, review_history, run_checkpoint, task
import test_reliability

resolver = test_reliability.resolver
from transaction import publish, recover


FACTS = dict(git_head="abc123", git_base="base123", git_branch="feature", worktree_dirty=False)
SCRIPTS = Path(__file__).parent


class FlexibleRoutingTests(unittest.TestCase):
    def test_small_task_skips_separate_triage(self):
        result = decide(task(Path('/tmp')), assurance(), [], 'INTAKE', 'aligned',
                        proposed_next='IMPLEMENTATION', route_reason='Local inspection resolved the relevant uncertainty.')
        self.assertEqual('IMPLEMENTATION', result.next_lifecycle)

    def test_uninspected_task_cannot_skip_investigation(self):
        for assessment in ('', None, False, 0, {}):
            with self.subTest(assessment=assessment), self.assertRaisesRegex(ValueError, 'repository findings'):
                decide(task(Path('/tmp')), assurance(assessment=assessment), [], 'INTAKE', 'aligned',
                       proposed_next='IMPLEMENTATION', route_reason='The request is short.')

    def test_sensitive_task_cannot_skip_plan_approval(self):
        document = assurance(sensitive_change=True, plan_assurance_required=True)
        with self.assertRaisesRegex(ValueError, 'independent approval'):
            decide(task(Path('/tmp')), document, [], 'INTAKE', 'aligned',
                   proposed_next='IMPLEMENTATION', route_reason='Only one line changes.')
        result = decide(task(Path('/tmp')), document, [], 'INTAKE', 'aligned',
                        proposed_next='PLAN_ASSURANCE', route_reason='The change affects authorization.')
        self.assertEqual('PLAN_ASSURANCE', result.next_lifecycle)

    def test_plan_approval_is_bound_to_current_plan_and_independent_worker(self):
        document = assurance(plan_assurance_required=True)
        approval = dict(lifecycle='PLAN_ASSURANCE', outcome='approve', task_revision=1,
                        worker_id='planner-reviewer', plan_fingerprint=plan_fingerprint(document))
        self.assertEqual([], prerequisite_errors(task(Path('/tmp')), document, [approval], 'IMPLEMENTATION', worker_id='builder'))
        self.assertTrue(prerequisite_errors(task(Path('/tmp')), document, [approval], 'IMPLEMENTATION', worker_id='planner-reviewer'))
        document['steps'] = ['Use a different persistence mechanism.']
        self.assertTrue(prerequisite_errors(task(Path('/tmp')), document, [approval], 'IMPLEMENTATION', worker_id='builder'))

    def test_new_evidence_can_return_to_investigation(self):
        for lifecycle in ('IMPLEMENTATION', 'CHANGE_ASSURANCE'):
            result = decide(task(Path('/tmp')), assurance(), [], lifecycle, 'needs_triage')
            self.assertEqual('TRIAGE', result.next_lifecycle)
            self.assertFalse(result.stop)

    def test_changed_risk_does_not_automatically_require_human_input(self):
        document = assurance()
        document['routing']['risk_changed'] = True
        self.assertEqual('TRIAGE', decide(task(Path('/tmp')), document, [], 'IMPLEMENTATION', 'needs_triage').next_lifecycle)

    def test_unsupported_completion_and_self_review_are_rejected(self):
        result = decide(task(Path('/tmp')), assurance(verdict='pass'), [], 'COMPLETED', 'complete', **FACTS)
        self.assertEqual('CHANGE_ASSURANCE', result.next_lifecycle)
        result = decide(task(Path('/tmp')), assurance(verdict='pass'), implementation_history(),
                        'CHANGE_ASSURANCE', 'pass', worker_id='implementer', **FACTS)
        self.assertEqual('CHANGE_ASSURANCE', result.next_lifecycle)
        result = decide(task(Path('/tmp')), assurance(verdict='pass'), review_history(), 'COMPLETED', 'complete', **FACTS)
        self.assertIsNone(result.next_lifecycle)

    def test_material_risk_needs_executed_proof(self):
        document = assurance(risks=[dict(behavior='Interrupted writes preserve source data.', evidence=[])])
        self.assertTrue(validate_acceptance(task(Path('/tmp')), document))
        document['risks'][0]['evidence'] = ['evidence-1']
        self.assertEqual([], validate_acceptance(task(Path('/tmp')), document))
        document['evidence'][0]['state'] = 'planned'
        self.assertTrue(validate_acceptance(task(Path('/tmp')), document))

    def test_changed_files_need_complete_behavior_mapping(self):
        document = assurance()
        self.assertTrue(validate_acceptance(task(Path('/tmp')), document, ['feature.py']))
        document['diff_groups'] = [dict(files=['feature.py'], path='path-1')]
        self.assertEqual([], validate_acceptance(task(Path('/tmp')), document, ['feature.py']))
        self.assertTrue(validate_acceptance(task(Path('/tmp')), document, ['feature.py', 'consumer.py']))
        document['diff_groups'][0]['path'] = 'unknown'
        self.assertTrue(validate_acceptance(task(Path('/tmp')), document, ['feature.py']))

    def test_bounded_implementation_preserves_incomplete_parent_requirements(self):
        document = assurance()
        document['evidence'][0].update(state='planned', result='pending')
        result = decide(task(Path('/tmp')), document, [], 'IMPLEMENTATION', 'in_progress')
        self.assertEqual('IMPLEMENTATION', result.next_lifecycle)
        result = decide(task(Path('/tmp')), document, [], 'IMPLEMENTATION', 'complete', **FACTS)
        self.assertEqual('IMPLEMENTATION', result.next_lifecycle)

    def test_time_pause_preserves_successful_review(self):
        history = review_history()
        history[-1].update(next_lifecycle='AWAITING_INPUT', resume_lifecycle='COMPLETED')
        result = decide(task(Path('/tmp')), assurance(verdict='pass'), history, 'COMPLETED', 'complete', **FACTS)
        self.assertIsNone(result.next_lifecycle)

    def test_later_failure_or_changed_risk_invalidates_old_review(self):
        history = review_history()
        history.append(dict(history[-1], outcome='fail', next_lifecycle='IMPLEMENTATION'))
        result = decide(task(Path('/tmp')), assurance(verdict='pass'), history, 'COMPLETED', 'complete', **FACTS)
        self.assertEqual('CHANGE_ASSURANCE', result.next_lifecycle)
        document = assurance(verdict='pass', risks=[dict(behavior='Preserve interrupted work.', evidence=['evidence-1'])])
        result = decide(task(Path('/tmp')), document, review_history(), 'COMPLETED', 'complete', **FACTS)
        self.assertEqual('CHANGE_ASSURANCE', result.next_lifecycle)

    def test_time_and_no_progress_stop_automatic_work(self):
        contract = task(Path('/tmp'), continuation_mode='automatic')
        history = [dict(run_id='run', active_seconds=1790, progress=False)]
        for seconds, progress in ((15, True), (1, False)):
            result = decide(contract, assurance(), history, 'TRIAGE', 'ready',
                            run_id='run', active_seconds=seconds, progress=progress)
            self.assertTrue(result.stop)
        result = decide(contract, assurance(), history, 'TRIAGE', 'ready',
                        run_id='new-run', active_seconds=1, progress=True)
        self.assertFalse(result.stop)


class FactoryExecutionTests(unittest.TestCase):
    setUp = test_reliability.RepositoryTests.setUp
    git = test_reliability.RepositoryTests.git

    def prepare(self):
        root = self.root / 'task'
        root.mkdir()
        head = self.git('rev-parse', 'HEAD')
        document = assurance(change_revision=head, base_revision=head)
        document['evidence'][0].update(revision=head, base_revision=head)
        (root / 'task.json').write_text(json.dumps(task(self.repository)))
        (root / 'assurance.json').write_text(json.dumps(document))
        (root / 'report.md').write_text('The requested behavior is ready for focused implementation.')
        return root, document

    def start(self, root, lifecycle, worker, *extra):
        return subprocess.run([sys.executable, str(SCRIPTS / 'start-assignment.py'), '--task-root', str(root),
                               '--lifecycle', lifecycle, '--worker-id', worker, '--reason', 'Current evidence supports this work.',
                               *extra], capture_output=True, text=True)

    def test_quick_route_records_boundaries_and_independent_review(self):
        root, document = self.prepare()
        result = run_checkpoint(root, 'INTAKE', 'aligned', '--next-lifecycle', 'IMPLEMENTATION',
                                '--route-reason', 'The repository assessment already covers this localized fix.')
        self.assertEqual(0, result.returncode, result.stderr)
        started = self.start(root, 'IMPLEMENTATION', 'implementation-worker')
        self.assertEqual(0, started.returncode, started.stderr)
        result = run_checkpoint(root, 'IMPLEMENTATION', 'complete')
        self.assertEqual('CHANGE_ASSURANCE', json.loads(result.stdout)['next_lifecycle'])
        self.assertNotEqual(0, self.start(root, 'CHANGE_ASSURANCE', 'implementation-worker').returncode)
        self.assertEqual(0, self.start(root, 'CHANGE_ASSURANCE', 'change_assurance-worker').returncode)
        document['verdict'] = 'pass'
        (root / 'assurance.json').write_text(json.dumps(document))
        self.assertEqual(0, run_checkpoint(root, 'CHANGE_ASSURANCE', 'pass').returncode)
        self.assertIsNone(json.loads(run_checkpoint(root, 'COMPLETED', 'complete').stdout)['next_lifecycle'])
        self.assertEqual([], validate_root(root))
        events = [json.loads(line) for line in (root / 'telemetry/events.jsonl').read_text().splitlines()]
        self.assertEqual(2, sum(item['event_type'] == 'run_started' for item in events))
        self.assertEqual(2, sum(item['event_type'] == 'actor_completed' for item in events))
        summary = SCRIPTS.parents[1] / 'factory-telemetry/scripts/summarize-events.py'
        result = subprocess.run([sys.executable, str(summary), '--task-root', str(root), '--strict'], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_telemetry_failure_does_not_block_checkpoint(self):
        root, _ = self.prepare()
        (root / 'telemetry').write_text('This path is unavailable.')
        result = run_checkpoint(root, 'INTAKE', 'aligned')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue((root / 'telemetry-warning.txt').exists())
        self.assertEqual([], validate_root(root))

    def test_automatic_route_records_one_complete_run(self):
        root, document = self.prepare()
        contract = json.loads((root / 'task.json').read_text())
        contract['continuation_mode'] = 'automatic'
        (root / 'task.json').write_text(json.dumps(contract))
        started = self.start(root, 'INTAKE', 'intake-worker')
        self.assertEqual(0, started.returncode, started.stderr)
        run_id = json.loads(started.stdout)['run_id']
        result = run_checkpoint(root, 'INTAKE', 'aligned', '--progress', 'yes', '--next-lifecycle', 'IMPLEMENTATION',
                                '--route-reason', 'The repository assessment supports direct implementation.')
        self.assertEqual(0, result.returncode, result.stderr)
        for lifecycle, outcome in (('IMPLEMENTATION', 'complete'), ('CHANGE_ASSURANCE', 'pass')):
            result = self.start(root, lifecycle, lifecycle.lower() + '-worker', '--run-id', run_id)
            self.assertEqual(0, result.returncode, result.stderr)
            if lifecycle == 'CHANGE_ASSURANCE':
                document['verdict'] = 'pass'
                (root / 'assurance.json').write_text(json.dumps(document))
            result = run_checkpoint(root, lifecycle, outcome, '--progress', 'yes')
            self.assertEqual(0, result.returncode, result.stderr)
        result = run_checkpoint(root, 'COMPLETED', 'complete')
        self.assertIsNone(json.loads(result.stdout)['next_lifecycle'])
        events = [json.loads(line) for line in (root / 'telemetry/events.jsonl').read_text().splitlines()]
        self.assertEqual(1, sum(item['event_type'] == 'run_started' for item in events))
        self.assertEqual(1, sum(item['event_type'] == 'run_finished' for item in events))
        summary = SCRIPTS.parents[1] / 'factory-telemetry/scripts/summarize-events.py'
        result = subprocess.run([sys.executable, str(summary), '--task-root', str(root), '--strict'], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_result_retry_and_stale_sequence(self):
        root, _ = self.prepare()
        first = run_checkpoint(root, 'INTAKE', 'aligned', '--result-id', 'result-1', '--expected-sequence', '0')
        self.assertEqual(0, first.returncode)
        before = (root / 'history.jsonl').read_text()
        repeated = run_checkpoint(root, 'INTAKE', 'aligned', '--result-id', 'result-1', '--expected-sequence', '0')
        self.assertTrue(json.loads(repeated.stdout)['replayed'])
        self.assertEqual(before, (root / 'history.jsonl').read_text())
        stale = run_checkpoint(root, 'TRIAGE', 'ready', '--result-id', 'result-2', '--expected-sequence', '0')
        self.assertNotEqual(0, stale.returncode)

    def test_retry_closes_assignment_left_after_accepted_checkpoint(self):
        root, _ = self.prepare()
        self.assertEqual(0, self.start(root, 'IMPLEMENTATION', 'implementation-worker').returncode)
        assignment = (root / 'assignment.json').read_text()
        result = run_checkpoint(root, 'IMPLEMENTATION', 'complete', '--result-id', 'completed-result')
        self.assertEqual(0, result.returncode, result.stderr)
        (root / 'assignment.json').write_text(assignment)
        before = (root / 'history.jsonl').read_text()
        repeated = run_checkpoint(root, 'IMPLEMENTATION', 'complete', '--result-id', 'completed-result')
        self.assertEqual(0, repeated.returncode, repeated.stderr)
        self.assertFalse((root / 'assignment.json').exists())
        self.assertEqual(before, (root / 'history.jsonl').read_text())

    def test_concurrent_checkpoints_cannot_duplicate_sequence(self):
        root, _ = self.prepare()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: run_checkpoint(root, 'INTAKE', 'aligned', '--expected-sequence', '0'), range(2)))
        self.assertEqual([0, 1], sorted(result.returncode for result in results))
        self.assertEqual(1, len((root / 'history.jsonl').read_text().splitlines()))

    def test_staged_update_and_interrupted_publication_recover(self):
        root, _ = self.prepare()
        source = self.root / 'prepared'
        source.mkdir()
        for name in ('task.json', 'assurance.json', 'report.md'):
            (source / name).write_text((root / name).read_text())
        (source / 'report.md').write_text('The current implementation is ready.')
        result = run_checkpoint(root, 'TRIAGE', 'ready', '--input-dir', str(source), '--result-id', 'prepared-result')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual((source / 'report.md').read_text(), (root / 'report.md').read_text())
        record = json.loads((root / 'history.jsonl').read_text())
        record.update(sequence=2, result_id='recovery-result')
        (source / 'report.md').write_text('Recovered current result.')
        import transaction
        original = transaction.replace_text
        def fail_on_report(path, text):
            if path.name == 'report.md':
                raise OSError('Simulated interruption')
            original(path, text)
        with patch('transaction.replace_text', side_effect=fail_on_report):
            with self.assertRaises(OSError):
                publish(root, source, record)
        self.assertTrue((root / 'pending-checkpoint.json').exists())
        self.assertEqual(record, recover(root))
        self.assertIsNone(recover(root))
        self.assertEqual('Recovered current result.', (root / 'report.md').read_text())
        self.assertEqual(2, len((root / 'history.jsonl').read_text().splitlines()))

    def test_accepted_contract_cannot_silently_change(self):
        root, _ = self.prepare()
        self.assertEqual(0, run_checkpoint(root, 'INTAKE', 'aligned').returncode)
        contract = json.loads((root / 'task.json').read_text())
        contract['acceptance_criteria'] = ['A weaker condition.']
        (root / 'task.json').write_text(json.dumps(contract))
        self.assertNotEqual(0, run_checkpoint(root, 'TRIAGE', 'ready').returncode)

    def test_repository_and_branch_names_do_not_collide(self):
        database = self.root / 'database'
        first = resolver.resolve(self.repository, database)['task_root']
        other = self.root / 'other' / self.repository.name
        other.mkdir(parents=True)
        subprocess.run(['git', 'clone', '-q', str(self.repository), str(other)], check=True)
        self.assertNotEqual(first, resolver.resolve(other, database)['task_root'])
        self.git('checkout', '-qb', 'topic/a')
        first = resolver.resolve(self.repository, database)['task_root']
        self.git('checkout', '-qb', 'topic--a')
        self.assertNotEqual(first, resolver.resolve(self.repository, database)['task_root'])

    def test_timed_check_preserves_failure_and_sanitizes_receipt(self):
        root, _ = self.prepare()
        script = SCRIPTS.parents[1] / 'factory-telemetry/scripts/run-check.py'
        result = subprocess.run([sys.executable, str(script), '--task-root', str(root), '--cwd', str(self.repository),
                                 '--proof', 'Focused validation', '--environment', 'token=private local test fixture',
                                 '--', sys.executable, '-c', 'raise SystemExit(3)'], capture_output=True, text=True)
        self.assertEqual(3, result.returncode, result.stderr)
        receipt = json.loads(next((root / 'artifacts/checks').glob('*.json')).read_text())
        self.assertEqual('fail', receipt['result'])
        self.assertEqual(3, receipt['exit_status'])
        self.assertNotIn('private', receipt['environment'])
        self.assertEqual(self.git('rev-parse', 'HEAD'), receipt['revision'])

    def test_timed_check_stops_at_timeout(self):
        root, _ = self.prepare()
        script = SCRIPTS.parents[1] / 'factory-telemetry/scripts/run-check.py'
        result = subprocess.run([sys.executable, str(script), '--task-root', str(root), '--cwd', str(self.repository),
                                 '--proof', 'Timeout test', '--environment', 'Local process', '--timeout', '0.05',
                                 '--', sys.executable, '-c', 'import time; time.sleep(10)'],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(124, result.returncode, result.stderr)

    def test_obsolete_assignment_cannot_submit_changed_contract(self):
        root, document = self.prepare()
        self.assertEqual(0, self.start(root, 'IMPLEMENTATION', 'implementation-worker').returncode)
        contract = json.loads((root / 'task.json').read_text())
        contract['task_revision'] = 2
        document['task_revision'] = 2
        (root / 'task.json').write_text(json.dumps(contract))
        (root / 'assurance.json').write_text(json.dumps(document))
        result = run_checkpoint(root, 'IMPLEMENTATION', 'complete')
        self.assertNotEqual(0, result.returncode)
        self.assertIn('obsolete contract', result.stderr)


if __name__ == '__main__':
    unittest.main()
