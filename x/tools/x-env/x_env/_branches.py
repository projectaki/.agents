"""Which branch a task uses: the fx branch rules as one pure function.

`decide` reads a `RefSnapshot` and returns either the information it still
needs (`Fetch`, `SetDefaultHead`) or the final checkout. `workspace.open_task`
runs the loop:

    gathered = frozenset()
    while isinstance(step := decide(..., _git.snapshot(...), gathered), Gather):
        perform(step); gathered |= {step}

Each `Gather` step is asked for at most once, so the loop ends after at most
three snapshots. Every rule is a table test over snapshots, without git
(see tests/test_branches.py). Rejections raise `XEnvError` before any change.
"""

from __future__ import annotations

from dataclasses import dataclass

from ._git import RefSnapshot
from .model import (
    BranchName,
    BranchRequest,
    DefaultBranch,
    StackOnto,
    TaskName,
    UseBase,
    XEnvError,
    feature_branch,
    legacy_branches,
)


# --- What the caller has to gather ------------------------------------------------


@dataclass(frozen=True)
class Fetch:
    remote: str


@dataclass(frozen=True)
class SetDefaultHead:
    """`origin/HEAD` is unset: run `remote set-head origin --auto`."""


Gather = Fetch | SetDefaultHead


# --- Final decisions ------------------------------------------------------------------


@dataclass(frozen=True)
class NewBranch:
    """Create the branch at `start` in the same git command that checks it out."""

    start: str  # a full ref: `refs/remotes/origin/main` or `refs/heads/x`
    track: bool


@dataclass(frozen=True)
class Reopen:
    """The worktree already has the right branch. Change nothing; no fetch."""

    branch: BranchName


@dataclass(frozen=True)
class Switch:
    """Switch the existing worktree. Only allowed when it is clean."""

    branch: BranchName
    create: NewBranch | None


@dataclass(frozen=True)
class AddWorktree:
    branch: BranchName
    create: NewBranch | None


Checkout = Reopen | Switch | AddWorktree


@dataclass(frozen=True)
class Current:
    """The existing worktree's branch. Detached worktrees never get here:
    `workspace` rejects them first."""

    branch: BranchName


def probes(request: BranchRequest) -> tuple[str, ...]:
    """The names whose `RefSnapshot.commitish` membership `decide` reads."""
    match request:
        case StackOnto(_, new_branch):
            return (new_branch,)
        case UseBase(branch):
            return (branch,)
        case DefaultBranch():
            return ()


def decide(
    task: TaskName,
    request: BranchRequest,
    current: Current | None,
    refs: RefSnapshot,
    gathered: frozenset[Gather],
) -> Gather | Checkout:
    """The fx rules. Pure: same inputs, same answer.

    A branch checked out in any other worktree (`refs.checked_out`, the clone
    included) is rejected with "already checked out". Never forces.
    """
    match request:
        case StackOnto(start, new_branch):
            return _stack_onto(start, new_branch, current, refs, gathered)
        case UseBase(base):
            return _use_base(base, current, refs, gathered)
        case DefaultBranch():
            return _default(task, current, refs, gathered)


def _stack_onto(
    start: BranchName,
    branch: BranchName,
    current: Current | None,
    refs: RefSnapshot,
    gathered: frozenset[Gather],
) -> Gather | Checkout:
    if current is not None:
        raise XEnvError("The task worktree already exists. Omit --onto to reopen it.")
    if branch in refs.commitish or branch.ref in refs.local:
        raise XEnvError(
            f"Use a new branch name with --onto. A branch, tag, or commit already matches: {branch}"
        )
    if Fetch("origin") not in gathered:
        return Fetch("origin")
    if f"refs/remotes/origin/{branch}" in refs.remote_tracking:
        raise XEnvError(
            f"Branch already exists on origin: {branch}. Choose a new branch name or omit --onto."
        )
    remote = _remote_prefix(start, refs.remotes)
    if remote:
        if remote != "origin" and Fetch(remote) not in gathered:
            return Fetch(remote)
        ref = f"refs/remotes/{start}"
    elif start.ref in refs.local:
        ref = start.ref
    else:
        ref = f"refs/remotes/origin/{start}"
    if ref not in refs.local and ref not in refs.remote_tracking:
        raise XEnvError(f"Start branch for --onto not found: {start}")
    return AddWorktree(branch, NewBranch(refs.remote_tracking.get(ref, ref), track=False))


def _use_base(
    base: BranchName,
    current: Current | None,
    refs: RefSnapshot,
    gathered: frozenset[Gather],
) -> Gather | Checkout:
    if base.ref in refs.local:
        return _place(base, None, current, refs)
    matched = _remote_prefix(base, refs.remotes)
    remote = matched or "origin"
    if Fetch(remote) not in gathered:
        return Fetch(remote)
    name = base.removeprefix(f"{remote}/") if matched else base
    target = refs.remote_tracking.get(f"refs/remotes/{remote}/{name}")
    if target is not None:
        branch = BranchName(target.removeprefix(f"refs/remotes/{remote}/"))
        create = None if branch.ref in refs.local else NewBranch(target, track=True)
        return _place(branch, create, current, refs)
    if matched:
        raise XEnvError(f"Remote base branch not found: {base}")
    if base in refs.commitish:
        raise XEnvError(f"The base must be a branch, not a tag or commit: {base}")
    start = _default_start(refs, gathered)
    if isinstance(start, SetDefaultHead):
        return start
    return _place(base, NewBranch(start, track=False), current, refs)


def _default(
    task: TaskName,
    current: Current | None,
    refs: RefSnapshot,
    gathered: frozenset[Gather],
) -> Gather | Checkout:
    if current is not None:
        return Reopen(current.branch)
    for branch in legacy_branches(task):
        if branch.ref in refs.local:
            return _place(branch, None, current, refs)
    if Fetch("origin") not in gathered:
        return Fetch("origin")
    start = _default_start(refs, gathered)
    if isinstance(start, SetDefaultHead):
        return start
    return AddWorktree(feature_branch(task), NewBranch(start, track=True))


def _default_start(refs: RefSnapshot, gathered: frozenset[Gather]) -> str | SetDefaultHead:
    """The full ref of origin's default branch, or the request to detect it."""
    target = refs.default_branch
    if target is None:
        if SetDefaultHead() not in gathered:
            return SetDefaultHead()
        raise XEnvError("The repository default branch is unknown. Supply --base <branch>.")
    if target not in refs.remote_tracking and target not in refs.local:
        raise XEnvError("The repository default branch is unavailable. Supply --base <branch>.")
    return target


def _place(
    branch: BranchName,
    create: NewBranch | None,
    current: Current | None,
    refs: RefSnapshot,
) -> Checkout:
    """Check `branch` out in the task: reopen, switch, or add the worktree.

    The current branch is tested first: git lets one branch live in only one
    worktree, so a branch that the task has is checked out nowhere else.
    """
    if current is not None and current.branch == branch:
        return Reopen(branch)
    holder = refs.checked_out.get(branch.ref)
    if holder is not None:
        raise XEnvError(f"Branch {branch} is already checked out in {holder}.")
    if current is None:
        return AddWorktree(branch, create)
    return Switch(branch, create)


def _remote_prefix(name: str, remotes: tuple[str, ...]) -> str | None:
    """The longest remote `r` such that `name` starts with `r/`."""
    matches = [r for r in remotes if name.startswith(f"{r}/")]
    return max(matches, key=len) if matches else None
