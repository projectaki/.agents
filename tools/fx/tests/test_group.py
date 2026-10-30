from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fx_context import save_response
from fx_group import comparison_context, resolve_group


class GroupNameTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.task = Path(self.temporary.name)
        self.root = self.task / "context/groups"
        self.root.mkdir(parents=True)

    def group(self, name):
        group = self.root / name
        group.mkdir()
        (group / "group.md").write_text("Group")
        return group

    def test_short_and_exact_names_resolve_to_the_same_group(self):
        group = self.group("review-Ab12Cd34")
        self.assertEqual(resolve_group(self.task, "review"), group)
        self.assertEqual(resolve_group(self.task, group.name), group)

    def test_similar_names_do_not_match_another_group(self):
        self.group("review-deep-Ab12Cd34")
        with self.assertRaisesRegex(ValueError, "not found"):
            resolve_group(self.task, "review")

    def test_ambiguous_name_lists_all_matches(self):
        first = self.group("review-Ab12Cd34")
        second = self.group("review-Ef56Gh78")
        with self.assertRaisesRegex(ValueError, "ambiguous") as error:
            resolve_group(self.task, "review")
        self.assertIn(first.name, str(error.exception))
        self.assertIn(second.name, str(error.exception))
        self.assertEqual(resolve_group(self.task, second.name), second)

    def test_invalid_names_are_rejected(self):
        for name in ("", "../review", "a/b", "--latest", "a*", "with spaces"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "name, not a path"):
                    resolve_group(self.task, name)

    def test_unmarked_directory_and_group_symlink_are_rejected(self):
        (self.root / "unmarked").mkdir()
        with self.assertRaisesRegex(ValueError, "Expected a group"):
            resolve_group(self.task, "unmarked")
        target = self.group("actual-Ab12Cd34")
        (self.root / "alias-Ab12Cd34").symlink_to(target)
        with self.assertRaisesRegex(ValueError, "Expected a group"):
            resolve_group(self.task, "alias")

    def test_comparison_context_includes_assignment_and_member_response(self):
        group = self.group("review-Ab12Cd34")
        (group / "initial_prompt.md").write_text("Review the login flow.")
        member = group / "1-agent"
        member.mkdir()
        (member / "instructions.md").write_text("Workspace guidance")
        (member / "tab-request.txt").write_text("accepted\n")
        save_response(member, "test-agent", "conversation", "turn", "Login needs input validation.")
        context = comparison_context(self.task, group)
        self.assertIn("Review the login flow.", context)
        self.assertIn("Login needs input validation.", context)

    def test_comparison_context_rejects_unaccepted_member_tab(self):
        group = self.group("review-Ab12Cd34")
        member = group / "1-agent"
        member.mkdir()
        (member / "instructions.md").write_text("Workspace guidance")
        for state in ("pending", "requesting", "failed: 23"):
            with self.subTest(state=state):
                (member / "tab-request.txt").write_text(state)
                with self.assertRaisesRegex(ValueError, "not accepted"):
                    comparison_context(self.task, group)


if __name__ == "__main__":
    unittest.main()
