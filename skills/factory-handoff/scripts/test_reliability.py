from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from records import validate_acceptance, validate_assurance, git_base_revision, validate_root, validate_task
from routing import decide
from test_records import SCRIPTS, assurance, task, run_checkpoint, review_history

spec = importlib.util.spec_from_file_location("resolver", SCRIPTS / "resolve-task-root.py")
resolver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolver)


class CompletionTests(unittest.TestCase):
    def route(self, document=None, contract=None, history=None, **facts):
        current = dict(git_head="abc123", git_base="base123", git_branch="feature", worktree_dirty=False)
        current.update(facts)
        return decide(contract or task(Path('/tmp')), document if document is not None else assurance(verdict="pass"), review_history() + (history or []), "COMPLETED", "complete", **current)

    def test_current_completion(self):
        self.assertIsNone(self.route().next_lifecycle)

    def test_each_current_fact_must_match(self):
        for field, value in (("git_head", "other"), ("git_head", None), ("git_base", "other"), ("git_base", None), ("git_branch", "other"), ("git_branch", None), ("worktree_dirty", True), ("worktree_dirty", None)):
            with self.subTest(field=field, value=value):
                self.assertEqual("IMPLEMENTATION", self.route(**{field: value}).next_lifecycle)

    def test_verdict_task_revision_and_blockers(self):
        for change in ({"verdict": "unverified"}, {"verdict": "fail"}, {"task_revision": 2}, {"blockers": ["Missing result"]}):
            with self.subTest(change=change):
                self.assertIsNotNone(self.route(document=assurance(**change)).next_lifecycle)

    def test_open_decision_prevents_completion(self):
        self.assertEqual("AWAITING_INPUT", self.route(contract=task(Path('/tmp'), open_decisions=["Choose behavior"])).next_lifecycle)

    def test_delivery_must_match_revision(self):
        contract = task(Path('/tmp'), deliverable="draft_pull_request")
        delivery = dict(lifecycle="DELIVERY", outcome="published", next_lifecycle="COMPLETED", git_head="abc123", git_base="base123", task_revision=1)
        self.assertEqual("AWAITING_INPUT", self.route(contract=contract).next_lifecycle)
        self.assertIsNone(self.route(contract=contract, history=[delivery]).next_lifecycle)
        delivery["git_head"] = "older"
        self.assertEqual("AWAITING_INPUT", self.route(contract=contract, history=[delivery]).next_lifecycle)

    def test_reopen_routes_changed_contract_to_triage(self):
        history = [dict(lifecycle="COMPLETED", status="terminal", task_revision=1)]
        for revision, target in ((1, "IMPLEMENTATION"), (2, "TRIAGE")):
            decision = decide(task(Path('/tmp'), task_revision=revision), assurance(task_revision=revision), history, "COMPLETED", "reopened")
            self.assertEqual(target, decision.next_lifecycle)
            self.assertFalse(decision.stop)
        decision = decide(task(Path('/tmp')), assurance(verdict="pass"), history, "COMPLETED", "reopened")
        self.assertEqual("AWAITING_INPUT", decision.next_lifecycle)


class AcceptanceTests(unittest.TestCase):
    def test_evidence_state_and_result_are_typed_before_acceptance(self):
        for state, result in (('planned', 'pending'), ('executed', 'pass'), ('executed', 'fail'), ('executed', 'blocked')):
            document = assurance()
            document['evidence'][0].update(state=state, result=result)
            self.assertEqual([], validate_assurance(document, 1))
        for item in (None, {}, {'state': 'done', 'result': 'pass'}, {'state': 'executed', 'result': 'Tests passed'}, {'state': [], 'result': {}}):
            with self.subTest(item=item):
                self.assertTrue(validate_assurance(assurance(evidence=[item]), 1))

    def test_complete_evidence(self):
        self.assertEqual([], validate_acceptance(task(Path('/tmp')), assurance()))

    def test_planned_checks_cannot_request_review(self):
        document = assurance()
        document['evidence'][0]['state'] = 'planned'
        decision = decide(task(Path('/tmp')), document, [], 'IMPLEMENTATION', 'complete',
                          git_head='abc123', git_base='base123', git_branch='feature', worktree_dirty=False)
        self.assertEqual('IMPLEMENTATION', decision.next_lifecycle)
        self.assertFalse(decision.stop)

    def test_related_session_requires_reference_and_relationship(self):
        contract = task(Path('/tmp'), related_sessions=[dict(reference='session://foundation', relationship='Foundation implementation')])
        self.assertEqual([], validate_task(contract))
        contract['related_sessions'][0].pop('reference')
        self.assertTrue(validate_task(contract))

    def test_missing_mapping_reference_proof_and_stale_evidence(self):
        for change in ({"paths": []}, {"evidence": []}):
            self.assertTrue(validate_acceptance(task(Path('/tmp')), assurance(**change)))
        for change in ({"proof": ""}, {"state": "planned"}, {"result": "fail"}, {"revision": "old"}, {"base_revision": "old"}, {"carried_from": "old"}):
            with self.subTest(change=change):
                document = assurance()
                document["evidence"][0].update(change)
                self.assertTrue(validate_acceptance(task(Path('/tmp')), document))

    def test_duplicate_evidence_reference(self):
        document = assurance()
        document["evidence"] *= 2
        self.assertTrue(validate_acceptance(task(Path('/tmp')), document))

    def test_exception_applies_only_to_named_behavior_and_revision(self):
        document = assurance(evidence=[])
        document["paths"][0].update(evidence=[], exception="exception-1")
        exception = dict(id="exception-1", behavior="The behavior is observable.", approval="Session approval reference", residual_risk="Visual spacing remains unverified", change_revision="abc123", base_revision="base123")
        document["exceptions"] = [exception]
        self.assertEqual([], validate_acceptance(task(Path('/tmp')), document))
        for field, value in (("behavior", "Another behavior"), ("residual_risk", ""), ("approval", ""), ("change_revision", "old"), ("base_revision", "old")):
            changed = copy.deepcopy(document)
            changed["exceptions"][0][field] = value
            self.assertTrue(validate_acceptance(task(Path('/tmp')), changed))

    def test_reused_result_requires_explicit_basis(self):
        document = assurance()
        document["evidence"][0].update(carried_from="old", reuse_reason="Only report text changed; tested source and dependencies are identical.")
        self.assertEqual([], validate_acceptance(task(Path('/tmp')), document))


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.repository = self.root / 'humanrisks-platform'
        self.repository.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Factory Test')
        self.git('config', 'user.email', 'factory@example.test')
        self.git('commit', '--allow-empty', '-qm', 'Initial state')
        self.git('branch', 'base')
        self.git('checkout', '-qb', 'feature')

    def git(self, *arguments):
        return subprocess.run(['git', '-C', str(self.repository), *arguments], text=True, capture_output=True, check=True).stdout.strip()

    def test_worktrees_share_identity_and_legacy_records_stay_in_place(self):
        worktree = self.root / '2098'
        self.git('worktree', 'add', '-qb', 'migration', str(worktree))
        database = self.root / 'database'
        legacy = database / '2098' / 'migration'
        legacy.mkdir(parents=True)
        (legacy / 'task.json').write_text(json.dumps(task(worktree)))
        result = resolver.resolve(worktree, database)
        self.assertTrue(Path(result['task_root']).parent.name.startswith('humanrisks-platform-'))
        self.assertTrue(Path(result['task_root']).name.startswith('migration-'))
        self.assertEqual(resolver.repository_identity(self.repository), resolver.repository_identity(worktree))
        self.assertEqual([str(legacy)], result['legacy_task_roots'])
        self.assertTrue((legacy / 'task.json').exists())
        self.assertFalse(Path(result['task_root']).exists())
        self.git('worktree', 'remove', str(worktree))
        self.git('checkout', '-q', 'migration')
        result = resolver.resolve(self.repository, database)
        self.assertEqual([str(legacy)], result['unresolved_task_roots'])

    def test_detached_and_non_git_identity(self):
        self.git('checkout', '--detach', '-q')
        result = resolver.resolve(self.repository, self.root / 'database')
        self.assertTrue(Path(result['task_root']).name.startswith('detached-'))
        plain = self.root / 'Plain Folder'
        plain.mkdir()
        self.assertEqual((plain, 'plain-folder'), resolver.repository_identity(plain))
        self.assertEqual('codex--some-task', resolver.slugify('Codex/Some Task'))
        self.assertEqual('unknown', resolver.slugify('...'))

    def test_optional_worker_details_and_compact_findings(self):
        records = self.root / 'records'
        records.mkdir()
        (records / 'task.json').write_text(json.dumps(task(self.repository)))
        (records / 'assurance.json').write_text(json.dumps(assurance()))
        (records / 'report.md').write_text('The bounded change is ready for implementation.')
        finding = dict(kind='missed_defect', summary='Completion skipped the revision check.', revision=self.git('rev-parse', 'HEAD'), evidence='artifact://completion-test')
        result = run_checkpoint(records, 'TRIAGE', 'ready', '--worker-id', 'worker-1', '--active-seconds', '12.5', '--finding', json.dumps(finding), '--decision', 'Use local deterministic validation.')
        self.assertEqual(0, result.returncode, result.stderr)
        record = json.loads((records / 'history.jsonl').read_text())
        self.assertEqual('worker-1', record['worker_id'])
        self.assertEqual(12.5, record['active_seconds'])
        self.assertEqual([finding], record['findings'])
        result = run_checkpoint(records, 'TRIAGE', 'ready')
        self.assertEqual(0, result.returncode, result.stderr)
        record = json.loads((records / 'history.jsonl').read_text().splitlines()[-1])
        self.assertIsNone(record['active_seconds'])
        self.assertEqual([], validate_root(records))
        for extra in (('--active-seconds', 'nan'), ('--finding', '{}')):
            result = run_checkpoint(records, 'TRIAGE', 'ready', *extra)
            self.assertNotEqual(0, result.returncode)

    def test_base_reference_tracks_target_updates(self):
        before = git_base_revision(self.repository, 'base')
        self.git('commit', '--allow-empty', '-qm', 'Dependency update')
        self.git('branch', '-f', 'base', 'HEAD')
        self.assertNotEqual(before, git_base_revision(self.repository, 'base'))
        self.assertIsNone(git_base_revision(self.repository, 'missing'))

    def test_invalid_checkpoint_and_preview_leave_records_unchanged(self):
        records = self.root / 'records'
        records.mkdir()
        (records / 'task.json').write_text(json.dumps(task(self.repository)))
        (records / 'assurance.json').write_text(json.dumps(assurance()))
        (records / 'report.md').write_text('The bounded change is ready for implementation.')
        for existing_history in (False, True):
            with self.subTest(existing_history=existing_history):
                if existing_history:
                    result = run_checkpoint(records, 'INTAKE', 'aligned')
                    self.assertEqual(0, result.returncode, result.stderr)
                before = {path.name: path.read_bytes() for path in records.iterdir() if path.is_file() and path.name != ".checkpoint.lock"}
                for lifecycle, outcome in (('TRIAGE', 'complete'), ('UNKNOWN', 'ready'), ('COMPLETED', 'ready')):
                    result = run_checkpoint(records, lifecycle, outcome)
                    self.assertNotEqual(0, result.returncode)
                    self.assertIn('Factory checkpoint failed', result.stderr)
                preview = run_checkpoint(records, 'TRIAGE', 'ready', '--preview')
                self.assertEqual(0, preview.returncode, preview.stderr)
                proposed = json.loads(preview.stdout)['record']
                self.assertEqual('IMPLEMENTATION', proposed['next_lifecycle'])
                self.assertFalse(proposed['stop'])
                self.assertEqual(before, {path.name: path.read_bytes() for path in records.iterdir() if path.is_file() and path.name != ".checkpoint.lock"})

        submitted = run_checkpoint(records, 'TRIAGE', 'ready')
        self.assertEqual(0, submitted.returncode, submitted.stderr)
        actual = json.loads((records / 'history.jsonl').read_text().splitlines()[-1])
        for field in ('sequence', 'next_lifecycle', 'stop', 'task_sha256', 'assurance_sha256', 'report_sha256'):
            self.assertEqual(proposed[field], actual[field])

    def test_preview_rejects_narrative_evidence_result(self):
        records = self.root / 'records'
        records.mkdir()
        document = assurance()
        document['evidence'][0]['result'] = 'Tests passed successfully'
        (records / 'task.json').write_text(json.dumps(task(self.repository)))
        (records / 'assurance.json').write_text(json.dumps(document))
        (records / 'report.md').write_text('The bounded change is ready for implementation.')
        result = run_checkpoint(records, 'TRIAGE', 'ready', '--preview')
        self.assertNotEqual(0, result.returncode)
        self.assertFalse((records / 'history.jsonl').exists())

    def test_checkpoint_normalizes_needs_input_outcome(self):
        records = self.root / 'records'
        records.mkdir()
        (records / 'task.json').write_text(json.dumps(task(self.repository)))
        (records / 'report.md').write_text('A product behavior decision is required.')
        result = run_checkpoint(records, 'INTAKE', 'NEEDS-INPUT')
        self.assertEqual(0, result.returncode, result.stderr)
        actual = json.loads((records / 'history.jsonl').read_text())
        self.assertEqual('needs_input', actual['outcome'])
        self.assertEqual('AWAITING_INPUT', actual['next_lifecycle'])
        self.assertTrue(actual['stop'])

    def test_checkpoint_cannot_record_stale_completion_as_terminal(self):
        records = self.root / 'records'
        records.mkdir()
        head = self.git('rev-parse', 'HEAD')
        document = assurance(verdict="pass", change_revision=head, base_revision=head)
        document['evidence'][0].update(revision=head, base_revision=head)
        (records / 'task.json').write_text(json.dumps(task(self.repository)))
        (records / 'assurance.json').write_text(json.dumps(document))
        (records / 'report.md').write_text('The required behavior passed focused checks.')
        run_checkpoint(records, 'IMPLEMENTATION', 'complete')
        run_checkpoint(records, 'CHANGE_ASSURANCE', 'pass')
        result = run_checkpoint(records, 'COMPLETED', 'complete')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual([], validate_root(records))
        earlier = (records / 'history.jsonl').read_text()
        self.git('commit', '--allow-empty', '-qm', 'Follow-up work')
        result = run_checkpoint(records, 'COMPLETED', 'complete')
        self.assertEqual('IMPLEMENTATION', json.loads(result.stdout)['next_lifecycle'])
        latest = json.loads((records / 'history.jsonl').read_text().splitlines()[-1])
        self.assertEqual('checkpointed', latest['status'])
        self.assertTrue((records / 'history.jsonl').read_text().startswith(earlier))
        result = run_checkpoint(records, 'IMPLEMENTATION', 'complete')
        self.assertNotEqual(0, result.returncode)
        document['verdict'] = 'unverified'
        (records / 'assurance.json').write_text(json.dumps(document))
        (records / 'report.md').write_text('Authorized follow-up work needs fresh assurance.')
        result = run_checkpoint(records, 'COMPLETED', 'reopened')
        self.assertEqual('IMPLEMENTATION', json.loads(result.stdout)['next_lifecycle'])
        self.assertEqual([], validate_root(records))


if __name__ == '__main__':
    unittest.main()
