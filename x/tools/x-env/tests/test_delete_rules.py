"""The delete rules (`workspace.decide_delete`) as a table, without git."""

import unittest

from x_env.model import XEnvError
from x_env.workspace import DeleteFacts, DeletePlan, decide_delete


def facts(dir_exists=True, registered=True, source_exists=True, locked=False, detached=False, dirty=False):
    return DeleteFacts(dir_exists, registered, source_exists, locked, detached, dirty)


class DecideDeleteTest(unittest.TestCase):
    def test_clean_task_removes_registration_and_folder(self):
        for force in (False, True):
            with self.subTest(force=force):
                self.assertEqual(decide_delete(facts(), force), DeletePlan(True, True))

    def test_rejections(self):
        cases = (
            ("locked", facts(locked=True), True),
            ("locked", facts(locked=True, source_exists=False, dir_exists=False), True),
            ("not registered", facts(registered=False), True),
            ("detached", facts(detached=True), False),
            ("--force", facts(dirty=True), False),
        )
        for message, observed, force in cases:
            with self.subTest(message=message, facts=observed):
                with self.assertRaisesRegex(XEnvError, message):
                    decide_delete(observed, force)

    def test_force_discards_dirty_and_detached_worktrees(self):
        self.assertEqual(decide_delete(facts(dirty=True, detached=True), True), DeletePlan(True, True))

    def test_partial_leftovers_remove_only_what_exists(self):
        cases = (
            (facts(source_exists=False), DeletePlan(True, True)),
            (facts(source_exists=False, dir_exists=False), DeletePlan(True, False)),
            (facts(source_exists=False, registered=False), DeletePlan(False, True)),
            (facts(source_exists=False, registered=False, dir_exists=False), DeletePlan(False, False)),
        )
        for observed, expected in cases:
            with self.subTest(facts=observed):
                self.assertEqual(decide_delete(observed, False), expected)

    def test_state_of_a_missing_source_is_ignored(self):
        observed = facts(source_exists=False, detached=True, dirty=True)
        self.assertEqual(decide_delete(observed, False), DeletePlan(True, True))


if __name__ == "__main__":
    unittest.main()
