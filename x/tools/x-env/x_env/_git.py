"""The only place that runs `git` (and `gh`). Private to the package.

Every function takes explicit paths, returns domain values, and raises
`GitError` with the command and stderr. No function here decides policy:
which branch to use lives in `_branches`, and the order of steps lives in
`workspace`.

Progress output from git goes to our stderr, as in fx, so the user sees clone
and fetch progress. Parsed output is captured.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .model import BranchName, GitHubRepo, GitUrl, LocalRepo, RepoSource, UsageError, XEnvError

_REDIRECTING_VARIABLES = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR")


class GitError(XEnvError):
    """A git command failed. `str()` is the user-facing message."""

    def __init__(self, message: str, argv: Sequence[str], stderr: str) -> None:
        super().__init__(message)
        self.argv = tuple(argv)
        self.stderr = stderr


def _environment() -> dict[str, str]:
    """The inherited environment without variables that redirect git, because
    a hook or a parent git process can set them."""
    return {k: v for k, v in os.environ.items() if k not in _REDIRECTING_VARIABLES}


def _command(repo: Path | None, args: Sequence[str]) -> list[str]:
    return ["git", *(["-C", str(repo)] if repo is not None else []), *args]


def _run(repo: Path | None, *args: str, capture: bool = True) -> str:
    """Run `git -C <repo> <args>` and return its stdout.

    With `capture=False`, git's output goes to our stderr (progress for the
    user) and the result is "".
    """
    argv = _command(repo, args)
    if capture:
        result = subprocess.run(argv, env=_environment(), capture_output=True, text=True)
    else:
        result = subprocess.run(argv, env=_environment(), stdout=sys.stderr, text=True)
    if result.returncode != 0:
        stderr = result.stderr or ""
        detail = stderr.strip().splitlines()[-1] if stderr.strip() else f"exit {result.returncode}"
        raise GitError(f"git {args[0]} failed: {detail}", argv, stderr)
    return result.stdout if capture else ""


def _probe(repo: Path | None, *args: str) -> tuple[int, str]:
    """Run a git query whose exit code is an answer. Returns (code, stdout)."""
    result = subprocess.run(
        _command(repo, args), env=_environment(), capture_output=True, text=True
    )
    return result.returncode, result.stdout


# --- Values read from git -------------------------------------------------------


@dataclass(frozen=True)
class RefSnapshot:
    """Everything `_branches.decide` needs to know about one clone's refs.

    Read in one pass after each fetch. Every ref is a full name, such as
    `refs/heads/origin/x` or `refs/remotes/origin/x`, so a local branch named
    `origin/x` and the remote branch `origin/x` can never be confused.
    """

    local: frozenset[str]
    """Full names of `refs/heads/*`."""
    remote_tracking: Mapping[str, str]
    """Full `refs/remotes/<r>/<b>` -> the full ref it points to. A symbolic ref
    of any remote, such as `refs/remotes/upstream/HEAD`, maps to its target.
    Others map to themselves."""
    remotes: tuple[str, ...]
    """Configured remote names. A name may contain `/`."""
    checked_out: Mapping[str, Path]
    """Full branch ref -> the worktree that has it checked out (the clone
    included)."""
    commitish: frozenset[str]
    """The probed names that resolve to a commit (tags, hashes, any branch)."""

    @property
    def default_branch(self) -> str | None:
        """Target of `refs/remotes/origin/HEAD`, such as
        `refs/remotes/origin/main`, if known."""
        return self.remote_tracking.get("refs/remotes/origin/HEAD")


@dataclass(frozen=True)
class Registration:
    """One entry of `git worktree list`, which may be stale."""

    branch: str | None  # full ref; None when detached
    locked: bool


def registered_worktrees(clone: Path) -> Mapping[Path, Registration]:
    """`git worktree list --porcelain -z`, the clone included. Stale entries
    are included, so a lock is visible even when the worktree folder is gone."""
    entries: dict[Path, Registration] = {}
    for record in _run(clone, "worktree", "list", "--porcelain", "-z").split("\0\0"):
        fields = [f for f in record.split("\0") if f]
        if not fields:
            continue
        path = Path(fields[0].removeprefix("worktree "))
        branch = next((f.removeprefix("branch ") for f in fields if f.startswith("branch ")), None)
        locked = any(f == "locked" or f.startswith("locked ") for f in fields)
        entries[path] = Registration(branch, locked)
    return entries


def snapshot(clone: Path, probe: Sequence[str] = ()) -> RefSnapshot:
    local: set[str] = set()
    tracking: dict[str, str] = {}
    output = _run(clone, "for-each-ref", "--format=%(refname)%00%(symref)", "refs/heads", "refs/remotes")
    for line in output.splitlines():
        ref, _, target = line.partition("\0")
        if ref.startswith("refs/heads/"):
            local.add(ref)
        else:
            tracking[ref] = target or ref
    commitish = frozenset(
        name for name in probe
        if _probe(clone, "rev-parse", "--verify", "--quiet", "--end-of-options", f"{name}^{{commit}}")[0] == 0
    )
    return RefSnapshot(
        local=frozenset(local),
        remote_tracking=tracking,
        remotes=tuple(_run(clone, "remote").split()),
        checked_out={r.branch: path for path, r in registered_worktrees(clone).items() if r.branch},
        commitish=commitish,
    )


def parse_branch(raw: str, option: str) -> BranchName:
    """Validate a branch name given to `--<option>`.

    Rejects a leading `-`, a `refs/` prefix, and anything that
    `git check-ref-format refs/heads/<raw>` rejects.
    Raises `UsageError("Invalid branch for --<option>: <raw>")`.
    """
    valid = (
        not raw.startswith(("-", "refs/"))
        and _probe(None, "check-ref-format", f"refs/heads/{raw}")[0] == 0
    )
    if not valid:
        raise UsageError(f"Invalid branch for --{option}: {raw}")
    return BranchName(raw)


@dataclass(frozen=True)
class WorktreeInfo:
    """What `delete` and `task` must know about an existing worktree path."""

    is_worktree: bool  # `<path>/.git` is a regular file and `path` is no symlink
    toplevel_matches: bool  # `rev-parse --show-toplevel` == path
    common_dir: Path | None  # resolved `--git-common-dir`
    branch: BranchName | None  # None when HEAD is detached


def toplevel(path: Path) -> Path:
    """`rev-parse --show-toplevel`: the root of the checkout that has `path`."""
    return Path(_run(path, "rev-parse", "--show-toplevel").strip())


def worktree_info(path: Path) -> WorktreeInfo:
    dot_git = path / ".git"
    if path.is_symlink() or dot_git.is_symlink() or not dot_git.is_file():
        return WorktreeInfo(False, False, None, None)
    common_dir = (path / _run(path, "rev-parse", "--git-common-dir").strip()).resolve()
    code, head = _probe(path, "symbolic-ref", "--quiet", "HEAD")
    head = head.strip()
    branch = BranchName(head.removeprefix("refs/heads/")) if code == 0 and head.startswith("refs/heads/") else None
    return WorktreeInfo(True, toplevel(path) == path, common_dir, branch)


def status_porcelain(path: Path, *, ignored: bool) -> str:
    """`status --porcelain --untracked-files=all [--ignored]`. Empty = clean."""
    return _run(path, "status", "--porcelain", "--untracked-files=all", *(["--ignored"] if ignored else []))


# --- Changes ---------------------------------------------------------------------


def clone(source: RepoSource, dest: Path) -> None:
    """`gh repo clone` for GitHubRepo, else `git clone -- <source> <dest>`.

    On failure, removes a partial `dest` so a retry starts clean.
    """
    match source:
        case GitHubRepo(owner, name):
            if shutil.which("gh") is None:
                raise XEnvError("Install and authenticate gh to clone an owner/repository name.")
            argv = ["gh", "repo", "clone", f"{owner}/{name}", str(dest)]
            label = f"{owner}/{name}"
        case GitUrl(url):
            argv = ["git", "clone", "--", url, str(dest)]
            label = url
        case LocalRepo(path):
            argv = ["git", "clone", "--", str(path), str(dest)]
            label = str(path)
    result = subprocess.run(argv, env=_environment(), stdout=sys.stderr)
    if result.returncode != 0:
        shutil.rmtree(dest, ignore_errors=True)
        raise GitError(f"Could not clone {label}. Fix the error above and run setup again.", argv, "")


def origin_url(clone: Path) -> str:
    return _run(clone, "remote", "get-url", "origin").strip()


def fetch(clone: Path, remote: str) -> None:
    """`fetch --no-tags --prune <remote>`.

    Raises `GitError("Could not fetch <remote>. No new task branch or worktree
    was created.")`. Callers fetch before any change, so that message is true.
    """
    try:
        _run(clone, "fetch", "--no-tags", "--prune", "--", remote, capture=False)
    except GitError as error:
        raise GitError(
            f"Could not fetch {remote}. No new task branch or worktree was created.",
            error.argv, error.stderr,
        ) from error


def set_default_head(clone: Path) -> None:
    """`remote set-head origin --auto`. Network access."""
    try:
        _run(clone, "remote", "set-head", "origin", "--auto", capture=False)
    except GitError as error:
        raise GitError(
            "Could not detect the default branch of origin. Supply --base <branch>.",
            error.argv, error.stderr,
        ) from error


def _track_option(track: bool) -> str:
    return "--track" if track else "--no-track"


def worktree_add(
    clone: Path,
    path: Path,
    branch: BranchName,
    *,
    start: str | None = None,
    track: bool = False,
) -> None:
    """`worktree add <path> <branch>`; with `start`, create the branch in the
    same command: `worktree add [--track|--no-track] -b <branch> <path> <start>`.

    One command, so a crash never leaves a new branch without its worktree.
    """
    if start is None:
        _run(clone, "worktree", "add", str(path), branch, capture=False)
    else:
        _run(clone, "worktree", "add", _track_option(track), "-b", branch, str(path), start, capture=False)


def switch(
    worktree: Path, branch: BranchName, *, start: str | None = None, track: bool = False
) -> None:
    """`switch --no-overwrite-ignore [-c <branch> [--track|--no-track] <start>] <branch>`."""
    if start is None:
        _run(worktree, "switch", "--no-overwrite-ignore", branch, capture=False)
    else:
        _run(worktree, "switch", "--no-overwrite-ignore", _track_option(track), "-c", branch, start, capture=False)


def worktree_remove(clone: Path, path: Path, *, force: bool) -> None:
    """`worktree remove [--force] -- <path>`. Also clears a stale registration."""
    _run(clone, "worktree", "remove", *(["--force"] if force else []), "--", str(path), capture=False)


# --- Local files for a new worktree ------------------------------------------------


def local_files(clone: Path) -> list[str]:
    """Relative paths to copy from the clone into a worktree.

    Ignored files (`ls-files --others --ignored --exclude-standard -z`) plus
    untracked files that `.worktreeinclude` selects (`--exclude-from`).
    Raises `XEnvError` if `.worktreeinclude` exists and is not a regular file.
    """
    listing = _run(clone, "ls-files", "--others", "--ignored", "--exclude-standard", "-z")
    include = clone / ".worktreeinclude"
    if include.exists() or include.is_symlink():
        if include.is_symlink() or not include.is_file():
            raise XEnvError("The .worktreeinclude file must be a regular file.")
        listing += _run(clone, "ls-files", "--others", "--ignored", f"--exclude-from={include}", "-z")
    return list(dict.fromkeys(p for p in listing.split("\0") if p))


def is_tracked(worktree: Path, relative: str) -> bool:
    """`--literal-pathspecs ls-files --error-unmatch`. Exit 1 = False; other
    exit codes raise, because "unknown" must not be read as "untracked"."""
    argv = ("--literal-pathspecs", "-C", str(worktree), "ls-files", "--error-unmatch", "--", relative)
    code, _ = _probe(None, *argv)
    if code not in (0, 1):
        raise GitError(f"Could not check whether a task file is tracked: {relative}", argv, "")
    return code == 0
