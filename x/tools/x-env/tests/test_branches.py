"""The fx branch rules as table tests over snapshots, without git.

The git-backed behavior (copying local files, delete, offline reopen) is in
test_cli.py, ported from fx tests/test_fx.py, which drives the CLI against
real repositories in a temporary X_ENV_ROOT.
"""

import unittest
from pathlib import Path

from x_env._branches import (
    AddWorktree,
    Current,
    Fetch,
    NewBranch,
    Reopen,
    SetDefaultHead,
    Switch,
    decide,
)
from x_env._git import RefSnapshot
from x_env.model import BranchName as B
from x_env.model import DefaultBranch, StackOnto, TaskName, UseBase, XEnvError

CLONE = Path("/w/p/repo/main")
OTHER = Path("/w/p/tasks/other/repo")


def H(name):
    return f"refs/heads/{name}"


def R(name):
    return f"refs/remotes/{name}"


def refs(local=("main",), remote=("origin/main",), head="origin/main",
         remotes=("origin",), checked_out=None, commitish=()):
    tracking = {R(r): R(r) for r in remote}
    if head:
        tracking[R("origin/HEAD")] = R(head)
    return RefSnapshot(
        local=frozenset(H(b) for b in local),
        remote_tracking=tracking,
        remotes=tuple(remotes),
        checked_out={H(b): p for b, p in ({"main": CLONE} if checked_out is None else checked_out).items()},
        commitish=frozenset(commitish),
    )


NOTHING = frozenset()
ORIGIN = frozenset({Fetch("origin")})
fix = TaskName("fix")


class DefaultBranchTest(unittest.TestCase):
    def test_new_task_fetches_then_tracks_the_default_branch(self):
        self.assertEqual(decide(fix, DefaultBranch(), None, refs(), NOTHING), Fetch("origin"))
        self.assertEqual(
            decide(fix, DefaultBranch(), None, refs(), ORIGIN),
            AddWorktree(B("feature/fix"), NewBranch(R("origin/main"), track=True)),
        )

    def test_default_branch_with_another_name(self):
        snapshot = refs(local=("trunk",), remote=("origin/trunk",), head="origin/trunk",
                        checked_out={"trunk": CLONE})
        self.assertEqual(
            decide(fix, DefaultBranch(), None, snapshot, ORIGIN),
            AddWorktree(B("feature/fix"), NewBranch(R("origin/trunk"), track=True)),
        )

    def test_reopen_never_fetches(self):
        got = decide(fix, DefaultBranch(), Current(B("manual")), refs(), NOTHING)
        self.assertEqual(got, Reopen(B("manual")))

    def test_existing_task_branches_are_reused_in_priority_order_without_fetching(self):
        cases = (
            (("main", "feature/fix", "fix", "codex/fix"), "feature/fix"),
            (("main", "fix", "codex/fix"), "fix"),
            (("main", "codex/fix"), "codex/fix"),
        )
        for local, expected in cases:
            with self.subTest(local=local):
                got = decide(fix, DefaultBranch(), None, refs(local=local), NOTHING)
                self.assertEqual(got, AddWorktree(B(expected), None))

    def test_existing_task_branch_checked_out_elsewhere_is_rejected(self):
        snapshot = refs(local=("main", "fix"), checked_out={"main": CLONE, "fix": OTHER})
        with self.assertRaisesRegex(XEnvError, "already checked out"):
            decide(fix, DefaultBranch(), None, snapshot, NOTHING)

    def test_unknown_default_asks_for_set_head_once(self):
        snapshot = refs(head=None)
        self.assertEqual(decide(fix, DefaultBranch(), None, snapshot, ORIGIN), SetDefaultHead())
        with self.assertRaisesRegex(XEnvError, "default branch is unknown"):
            decide(fix, DefaultBranch(), None, snapshot, ORIGIN | {SetDefaultHead()})

    def test_default_that_points_to_a_missing_ref_is_rejected(self):
        snapshot = refs(remote=(), head="origin/gone")
        with self.assertRaisesRegex(XEnvError, "default branch is unavailable"):
            decide(fix, DefaultBranch(), None, snapshot, ORIGIN)


class UseBaseTest(unittest.TestCase):
    def test_local_base_is_used_without_fetching(self):
        got = decide(fix, UseBase(B("export")), None, refs(local=("main", "export")), NOTHING)
        self.assertEqual(got, AddWorktree(B("export"), None))

    def test_base_checked_out_elsewhere_is_rejected(self):
        with self.assertRaisesRegex(XEnvError, "already checked out"):
            decide(fix, UseBase(B("main")), None, refs(), NOTHING)

    def test_base_equal_to_the_current_branch_reopens_without_fetching(self):
        snapshot = refs(local=("main", "feature/fix"),
                        checked_out={"main": CLONE, "feature/fix": Path("/w/p/tasks/fix/repo")})
        got = decide(fix, UseBase(B("feature/fix")), Current(B("feature/fix")), snapshot, NOTHING)
        self.assertEqual(got, Reopen(B("feature/fix")))

    def test_remote_base_on_existing_worktree_switches_and_creates_tracking_branch(self):
        snapshot = refs(remote=("origin/main", "origin/export"))
        self.assertEqual(
            decide(fix, UseBase(B("origin/export")), Current(B("feature/fix")), snapshot, NOTHING),
            Fetch("origin"),
        )
        self.assertEqual(
            decide(fix, UseBase(B("origin/export")), Current(B("feature/fix")), snapshot, ORIGIN),
            Switch(B("export"), NewBranch(R("origin/export"), track=True)),
        )

    def test_unprefixed_base_found_only_on_origin_gets_a_tracking_branch(self):
        got = decide(fix, UseBase(B("export")), None, refs(remote=("origin/main", "origin/export")), ORIGIN)
        self.assertEqual(got, AddWorktree(B("export"), NewBranch(R("origin/export"), track=True)))

    def test_remote_base_reuses_an_existing_local_branch(self):
        snapshot = refs(local=("main", "export"), remote=("origin/main", "origin/export"))
        got = decide(fix, UseBase(B("origin/export")), None, snapshot, ORIGIN)
        self.assertEqual(got, AddWorktree(B("export"), None))

    def test_local_branch_named_like_a_remote_branch_is_a_different_branch(self):
        local = refs(local=("main", "origin/export"), remote=("origin/main",))
        self.assertEqual(
            decide(fix, UseBase(B("origin/export")), None, local, NOTHING),
            AddWorktree(B("origin/export"), None),
        )
        remote = refs(local=("main",), remote=("origin/main", "origin/export"))
        self.assertEqual(
            decide(fix, UseBase(B("origin/export")), None, remote, ORIGIN),
            AddWorktree(B("export"), NewBranch(R("origin/export"), track=True)),
        )

    def test_base_on_a_remote_with_a_slash_fetches_that_remote(self):
        snapshot = refs(remote=("origin/main", "team/upstream/feature/export"),
                        remotes=("origin", "team", "team/upstream"))
        request = UseBase(B("team/upstream/feature/export"))
        self.assertEqual(decide(fix, request, None, snapshot, NOTHING), Fetch("team/upstream"))
        self.assertEqual(
            decide(fix, request, None, snapshot, frozenset({Fetch("team/upstream")})),
            AddWorktree(B("feature/export"), NewBranch(R("team/upstream/feature/export"), track=True)),
        )

    def test_symbolic_remote_ref_resolves_to_its_target_branch(self):
        snapshot = refs(local=(), remote=("origin/main",), checked_out={})
        got = decide(fix, UseBase(B("origin/HEAD")), None, snapshot, ORIGIN)
        self.assertEqual(got, AddWorktree(B("main"), NewBranch(R("origin/main"), track=True)))

    def test_missing_remote_base_is_an_error_not_a_new_branch(self):
        with self.assertRaisesRegex(XEnvError, "Remote base branch not found"):
            decide(fix, UseBase(B("origin/missing")), None, refs(), ORIGIN)

    def test_base_that_is_a_tag_or_commit_is_rejected(self):
        with self.assertRaisesRegex(XEnvError, "not a tag or commit"):
            decide(fix, UseBase(B("v1")), None, refs(commitish=("v1",)), ORIGIN)

    def test_new_base_starts_untracked_at_the_default_branch(self):
        got = decide(fix, UseBase(B("release/new")), None, refs(), ORIGIN)
        self.assertEqual(got, AddWorktree(B("release/new"), NewBranch(R("origin/main"), track=False)))

    def test_new_base_with_unknown_default_asks_for_set_head(self):
        self.assertEqual(decide(fix, UseBase(B("release/new")), None, refs(head=None), ORIGIN), SetDefaultHead())


class StackOntoTest(unittest.TestCase):
    def onto(self, start, new="feature/fix"):
        return StackOnto(B(start), B(new))

    def test_rejects_an_existing_worktree_before_fetching(self):
        with self.assertRaisesRegex(XEnvError, "Omit --onto"):
            decide(fix, self.onto("main"), Current(B("feature/fix")), refs(), NOTHING)

    def test_rejects_a_new_branch_name_that_already_exists_before_fetching(self):
        for snapshot in (refs(local=("main", "feature/fix")), refs(commitish=("feature/fix",))):
            with self.subTest(snapshot=snapshot):
                with self.assertRaisesRegex(XEnvError, "Use a new branch name"):
                    decide(fix, self.onto("main"), None, snapshot, NOTHING)

    def test_rejects_a_new_branch_name_that_exists_on_origin(self):
        snapshot = refs(remote=("origin/main", "origin/feature/fix"))
        with self.assertRaisesRegex(XEnvError, "already exists on origin"):
            decide(fix, self.onto("main"), None, snapshot, ORIGIN)

    def test_starts_at_a_local_branch_without_upstream(self):
        snapshot = refs(local=("main", "feature/export"))
        self.assertEqual(decide(fix, self.onto("feature/export", "stacked"), None, snapshot, NOTHING), Fetch("origin"))
        self.assertEqual(
            decide(fix, self.onto("feature/export", "stacked"), None, snapshot, ORIGIN),
            AddWorktree(B("stacked"), NewBranch(H("feature/export"), track=False)),
        )

    def test_name_found_only_on_origin_starts_at_the_remote_tip(self):
        snapshot = refs(remote=("origin/main", "origin/remote-only"))
        got = decide(fix, self.onto("remote-only"), None, snapshot, ORIGIN)
        self.assertEqual(got, AddWorktree(B("feature/fix"), NewBranch(R("origin/remote-only"), track=False)))

    def test_remote_prefixed_start_uses_the_remote_branch_even_with_a_local_one(self):
        snapshot = refs(local=("main", "export"), remote=("origin/main", "origin/export"))
        got = decide(fix, self.onto("origin/export"), None, snapshot, ORIGIN)
        self.assertEqual(got, AddWorktree(B("feature/fix"), NewBranch(R("origin/export"), track=False)))

    def test_start_on_another_remote_fetches_it_and_does_not_track(self):
        snapshot = refs(remote=("origin/main", "team/upstream/export"), remotes=("origin", "team/upstream"))
        request = self.onto("team/upstream/export")
        self.assertEqual(decide(fix, request, None, snapshot, ORIGIN), Fetch("team/upstream"))
        self.assertEqual(
            decide(fix, request, None, snapshot, ORIGIN | {Fetch("team/upstream")}),
            AddWorktree(B("feature/fix"), NewBranch(R("team/upstream/export"), track=False)),
        )

    def test_missing_start_is_rejected(self):
        with self.assertRaisesRegex(XEnvError, "Start branch for --onto not found"):
            decide(fix, self.onto("missing"), None, refs(), ORIGIN)


if __name__ == "__main__":
    unittest.main()
