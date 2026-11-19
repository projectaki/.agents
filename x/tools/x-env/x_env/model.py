"""Domain types for x-env: names, projects, tasks, and sessions.

This module is pure. It does no I/O except `Path` arithmetic. Every path in the
layout is derived here, in one place, from a root and validated names:

    $X_ENV_ROOT/<project>/
      .x-env-project            marker, content "x-env-project-v1"
      .x-env.lock               flock target for task and delete
      repo/main/                the clone
      tasks/<task>/repo/        the task worktree
      tasks/<task>/AGENTS.md    short task instructions
      sessions/<task>/<nnn>-<name>/   session records (outlive the task)

Invariant: a `Name` or `BranchName` value is valid. Code that receives one
never validates it again (per boundary-discipline).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal

MARKER_FILE = ".x-env-project"
MARKER_CONTENT = "x-env-project-v1"
_NAME = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]*")
_GITHUB_PREFIXES = ("https://github.com/", "git@github.com:", "ssh://git@github.com/")


class XEnvError(Exception):
    """An expected failure. The CLI prints `x-env: <message>` and exits 1.

    The message says what was preserved and what to do next, as fx did
    ("No new task branch or worktree was created.").
    """


class UsageError(XEnvError):
    """Bad command-line input. The CLI exits 2."""


# --- Names -------------------------------------------------------------------


class Name(str):
    """A project, task, or session name. Valid by construction.

    It cannot hold `/`, `.`, or a leading `-`, so a name can never escape its
    parent folder or be read as an option.
    """

    def __new__(cls, raw: str) -> Name:
        if not _NAME.fullmatch(raw):
            raise UsageError(
                "Names must start with a letter or digit and contain only "
                "letters, digits, underscores, or hyphens."
            )
        return super().__new__(cls, raw)


class BranchName(str):
    """A local branch name that `git check-ref-format refs/heads/<name>` accepts.

    Construct it only with `_git.parse_branch` (the check needs git), or from a
    name that git already reported. The type exists so that a branch, a task
    name, and a ref such as `refs/remotes/x` cannot be mixed up.
    """

    @property
    def ref(self) -> str:
        """The full ref, `refs/heads/<name>`."""
        return f"refs/heads/{self}"


class ProjectName(Name):
    """A project name. A separate type, so a task name cannot be passed as one."""


class TaskName(Name):
    """A task name."""


class SessionName(Name):
    """A session name, the `<name>` in `<nnn>-<name>`."""


def feature_branch(task: TaskName) -> BranchName:
    """`feature/<task>`. A valid `Name` always makes a valid branch name."""
    return BranchName(f"feature/{task}")


def legacy_branches(task: TaskName) -> tuple[BranchName, ...]:
    """Branches that an existing task may already use, in priority order."""
    return (feature_branch(task), BranchName(task), BranchName(f"codex/{task}"))


# --- Branch request (the --base / --onto / --branch options) -------------------


@dataclass(frozen=True)
class DefaultBranch:
    """No option: reopen the current branch, or pick the task's branch."""


@dataclass(frozen=True)
class UseBase:
    """`--base <branch>`: work on an existing (or new, untracked) branch."""

    branch: BranchName


@dataclass(frozen=True)
class StackOnto:
    """`--onto <start> [--branch <new>]`: a new branch that starts at `start`.

    `new_branch` comes from `--branch`; the CLI fills in `feature/<task>` when
    it is absent, so the default lives in one place.
    """

    start: BranchName
    new_branch: BranchName


BranchRequest = DefaultBranch | UseBase | StackOnto


# --- Repository source (the setup argument) ----------------------------------


@dataclass(frozen=True)
class GitHubRepo:
    """`owner/name`. Cloned with `gh repo clone`."""

    owner: str
    name: str


@dataclass(frozen=True)
class GitUrl:
    url: str


@dataclass(frozen=True)
class LocalRepo:
    path: Path  # absolute and resolved at the boundary


RepoSource = GitHubRepo | GitUrl | LocalRepo


def repo_identity(source: RepoSource | str) -> str:
    """The comparable identity of a repository, for the setup origin check.

    A GitHub HTTPS URL, SSH URL, and `owner/name` all map to `owner/name`.
    A local path maps to itself. A raw string is an origin URL read from git
    config.
    """
    match source:
        case GitHubRepo(owner, name):
            raw = f"{owner}/{name}"
        case GitUrl(url):
            raw = url
        case LocalRepo(path):
            raw = str(path)
        case str():
            raw = source
    raw = raw.removesuffix("/").removesuffix(".git")
    for prefix in _GITHUB_PREFIXES:
        if raw.startswith(prefix):
            return raw.removeprefix(prefix)
    return raw


# --- Project and tasks ----------------------------------------------------------


@dataclass(frozen=True)
class Project:
    """A project folder. `path` is absolute and has no symbolic links."""

    path: Path

    @property
    def name(self) -> ProjectName:
        return ProjectName(self.path.name)

    @property
    def marker(self) -> Path:
        return self.path / MARKER_FILE

    @property
    def lock_file(self) -> Path:
        return self.path / ".x-env.lock"

    @property
    def clone(self) -> Path:
        return self.path / "repo" / "main"

    @property
    def tasks_dir(self) -> Path:
        return self.path / "tasks"

    @property
    def sessions_dir(self) -> Path:
        return self.path / "sessions"

    def task(self, name: TaskName) -> WorktreeTask:
        return WorktreeTask(self, name)


@dataclass(frozen=True)
class WorktreeTask:
    """A task with its own git worktree. Used on a local machine and a VPS."""

    project: Project
    name: TaskName

    @property
    def project_name(self) -> ProjectName:
        return self.project.name

    @property
    def dir(self) -> Path:
        return self.project.tasks_dir / self.name

    @property
    def source(self) -> Path:
        """The worktree, where agents edit code."""
        return self.dir / "repo"

    @property
    def agents_md(self) -> Path:
        return self.dir / "AGENTS.md"

    @property
    def records(self) -> Path:
        """Session records. Outside `dir`, so `delete` keeps them."""
        return self.project.sessions_dir / self.name


@dataclass(frozen=True)
class CheckoutTask:
    """A task in a cloud or sandbox checkout that is already isolated.

    No worktree and no `tasks/` folder: the checkout is the task. Records still
    go to `<root>/<project>/sessions/<task>/` so that every environment has
    one record layout.
    """

    root: Path
    project_name: ProjectName
    name: TaskName
    checkout: Path

    @property
    def source(self) -> Path:
        return self.checkout

    @property
    def records(self) -> Path:
        return self.root / self.project_name / "sessions" / self.name


Task = WorktreeTask | CheckoutTask
"""Sessions use only `name`, `project_name`, `source`, and `records`."""


# --- Sessions (types shared by records, sessions, and adapters) ----------------


class HarnessName(StrEnum):
    CLAUDE = "claude"
    CODEX = "codex"


class Access(StrEnum):
    """What the agent may do without asking. Each harness maps it to flags."""

    AUTO = "auto"
    FULL = "full"


Effort = Literal["low", "medium", "high", "xhigh", "max"]
Mode = Literal["visible", "headless"]


class SessionId(str):
    """`<task>/<nnn>-<name>`, unique within one project on one host.

    It is the record folder path relative to `<project>/sessions/`. `wait`,
    `resume`, and terminal labels all use it.
    """

    @staticmethod
    def of(task: TaskName, number: int, name: SessionName) -> SessionId:
        return SessionId(f"{task}/{number:03d}-{name}")

    def parse(self) -> tuple[TaskName, int, SessionName]:
        """Split into task, number, and name. Raise `UsageError` if malformed."""
        task, slash, folder = self.partition("/")
        number, dash, name = folder.partition("-")
        if not (slash and dash and number.isdigit() and number.isascii()):
            raise UsageError(f"Invalid session id: {self}. Use <task>/<nnn>-<name>.")
        return TaskName(task), int(number), SessionName(name)


def terminal_label(project: ProjectName, session: SessionId) -> str:
    """The tab label for a visible session: `<project>/<task>/<nnn>-<name>`.

    One derivation, so `rex ls` output can be matched back to records.
    """
    return f"{project}/{session}"
