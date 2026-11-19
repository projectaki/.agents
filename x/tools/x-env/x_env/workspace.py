"""Workspace: projects, tasks, and worktrees. Needs git only.

Public API (all a caller needs):

    setup(root, name, source)            -> Project
    find_project(cwd, root, name=None)   -> Project
    find_task(project, cwd, name=None)   -> WorktreeTask
    open_task(project, name, request)    -> WorktreeTask
    delete_task(project, name, force=..., stop_sessions=...)
    open_checkout_task(...)              -> CheckoutTask    (cloud; later step)

Every function is idempotent: it reads the current state, compares it with
the goal, and changes only the difference (per make-operations-idempotent).
Every rejection happens before the first change, and its message says what
was kept. Progress goes to the `x_env` logger, which the CLI prints to stderr
as `x-env: <message>`.
"""

from __future__ import annotations

import fcntl
import logging
import os
import secrets
import shutil
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from . import _git
from ._branches import (
    AddWorktree,
    Checkout,
    Current,
    Fetch,
    Gather,
    Reopen,
    SetDefaultHead,
    Switch,
    decide,
    probes,
)
from .model import (
    MARKER_CONTENT,
    BranchRequest,
    CheckoutTask,
    Project,
    ProjectName,
    RepoSource,
    TaskName,
    WorktreeTask,
    XEnvError,
    repo_identity,
)

log = logging.getLogger("x_env")


# --- Project ----------------------------------------------------------------------


def setup(root: Path, name: ProjectName, source: RepoSource | None) -> Project:
    """Create or confirm the project folder, and clone `source` once.

    - Creates `root`, the project folder, `repo/`, `tasks/`, `sessions/`, and
      the marker if missing. Rejects a symbolic link for any of them.
    - Existing clone: validates it. With `source`, the origin identity must
      match (`model.repo_identity`), else "The supplied repository differs
      from the existing origin. The clone was not changed." Never fetches,
      pulls, or resets.
    - No clone and `source`: clones into `repo/.main-partial-<random>` and
      renames it into place. A killed clone leaves only a partial folder,
      which the next setup removes.
    - No clone and no `source`: allowed. `task` then fails until a later
      `setup <name> <repo>` adds the clone.
    """
    project = Project(ensure_dir(root).resolve() / name)
    for directory in (project.path, project.clone.parent, project.tasks_dir, project.sessions_dir):
        ensure_dir(directory)
    _write_new_file(project.marker, MARKER_CONTENT + "\n")
    _check_marker(project)
    with _project_lock(project):
        if project.clone.exists() or project.clone.is_symlink():
            _validate_clone(project.clone)
            if source is not None and repo_identity(_git.origin_url(project.clone)) != repo_identity(source):
                raise XEnvError(
                    "The supplied repository differs from the existing origin. The clone was not changed."
                )
        elif source is not None:
            for leftover in project.clone.parent.glob(".main-partial-*"):
                shutil.rmtree(leftover)
            partial = project.clone.parent / f".main-partial-{secrets.token_hex(4)}"
            _git.clone(source, partial)
            _validate_clone(partial)
            partial.rename(project.clone)
    log.info("Project ready: %s", project.path)
    return project


def find_project(cwd: Path, root: Path, name: ProjectName | None = None) -> Project:
    """The project named by `--project`, else the nearest marker above `cwd`.

    `--project` exists for forwarded commands: the remote x-env does not run
    inside the project folder. Raises "Run this command inside a project
    created by x-env setup."
    """
    if name is not None:
        project = Project(root.resolve() / name)
        if not project.marker.is_file():
            raise XEnvError(f"Project not found: {project.path}. Run x-env setup {name} first.")
        _check_marker(project)
        return project
    for directory in (cwd.resolve(), *cwd.resolve().parents):
        project = Project(directory)
        if project.marker.is_file():
            _check_marker(project)
            return project
    raise XEnvError("Run this command inside a project created by x-env setup.")


def find_task(project: Project, cwd: Path, name: TaskName | None = None) -> WorktreeTask:
    """The task named by `--task`, else the task folder that holds `cwd`
    (`<project>/tasks/<task>/...`). Its worktree must exist."""
    if name is None:
        here = cwd.resolve()
        if not here.is_relative_to(project.tasks_dir) or here == project.tasks_dir:
            raise XEnvError("Run this command inside a task folder, or pass --task <name>.")
        name = TaskName(here.relative_to(project.tasks_dir).parts[0])
    task = project.task(name)
    if not task.source.is_dir():
        raise XEnvError(f"Task not found: {task.dir}. Run x-env task {name} first.")
    return task


def _check_marker(project: Project) -> None:
    if project.marker.is_symlink() or project.marker.read_text().rstrip("\n") != MARKER_CONTENT:
        raise XEnvError(f"Unsupported project marker: {project.marker}")


def _validate_clone(clone: Path) -> None:
    """`clone/.git` is a directory, `clone` is no symlink, and it is the git
    top level. Raises "Run x-env setup <project> <repository> first." when the
    clone is missing."""
    if not clone.exists() and not clone.is_symlink():
        project = clone.parent.parent.name
        raise XEnvError(f"The project has no clone. Run x-env setup {project} <repository> first.")
    if clone.is_symlink() or not (clone / ".git").is_dir():
        raise XEnvError(f"Expected a main repository clone: {clone}")
    if _git.toplevel(clone) != clone:
        raise XEnvError(f"Repository root does not match: {clone}")


# --- Task -----------------------------------------------------------------------------


def open_task(project: Project, name: TaskName, request: BranchRequest) -> WorktreeTask:
    """Create or reopen a task worktree and return the task.

    Order (each step safe to repeat):
      1. Validate the clone and reject symbolic links for the task folders.
      2. If `task.source` exists: it must be a worktree of this clone, at its
         own top level, with a branch checked out (`Current`). Else `None`.
      3. Decide the branch (`_branches.decide`), gathering fetches as asked.
         A failed fetch stops here, before any change.
      4. Create the task folder and apply the decision:
           Reopen      -> nothing.
           Switch      -> require `status --porcelain --untracked-files=all`
                          to be empty, then `_git.switch`.
           AddWorktree -> `_git.worktree_add` (creates the branch in the same
                          command when `create` is set).
      5. `_copy_local_files(project.clone, task.source)`.
      6. Write `AGENTS.md` if missing. Never overwrite it.
    """
    task = project.task(name)
    with _project_lock(project):
        _validate_clone(project.clone)
        for directory in (project.tasks_dir, task.dir):
            _reject_symlink(directory)
        current = _current(project, task)
        step = _decide_with_fetches(project, task, request, current)
        ensure_dir(project.tasks_dir)
        ensure_dir(task.dir)
        _apply(project, task, step)
        _copy_local_files(project.clone, task.source)
        _write_new_file(task.agents_md, task_agents_md(task))
    log.info("Task ready: %s", task.dir)
    return task


def _decide_with_fetches(
    project: Project, task: WorktreeTask, request: BranchRequest, current: Current | None
) -> Checkout:
    gathered: frozenset[Gather] = frozenset()
    while True:
        step = decide(task.name, request, current, _git.snapshot(project.clone, probes(request)), gathered)
        match step:
            case Fetch(remote):
                log.info("Fetching base updates from %s", remote)
                _git.fetch(project.clone, remote)
            case SetDefaultHead():
                _git.set_default_head(project.clone)
            case Reopen() | Switch() | AddWorktree():
                return step
        gathered |= {step}


def _apply(project: Project, task: WorktreeTask, step: Checkout) -> None:
    match step:
        case Reopen():
            return
        case Switch(branch, create):
            if _git.status_porcelain(task.source, ignored=False):
                raise XEnvError(
                    "The task has uncommitted or untracked files. Commit or save them before switching branches."
                )
            try:
                _git.switch(
                    task.source, branch,
                    start=create.start if create else None, track=bool(create and create.track),
                )
            except _git.GitError as error:
                raise XEnvError(
                    f"Could not switch the task to {branch}. The previous branch was preserved."
                ) from error
        case AddWorktree(branch, create):
            if create is not None:
                log.info("Creating task branch %s from %s", branch, create.start)
            _git.worktree_add(
                project.clone, task.source, branch,
                start=create.start if create else None, track=bool(create and create.track),
            )


def _validated_worktree(project: Project, task: WorktreeTask) -> _git.WorktreeInfo:
    """The worktree at `task.source`, which must belong to this clone."""
    info = _git.worktree_info(task.source)
    if not info.is_worktree:
        raise XEnvError(f"Expected a task worktree: {task.source}")
    if not info.toplevel_matches:
        raise XEnvError(f"Worktree root does not match: {task.source}")
    if info.common_dir != (project.clone / ".git").resolve():
        raise XEnvError("The task worktree belongs to another repository.")
    return info


def _current(project: Project, task: WorktreeTask) -> Current | None:
    """Validate an existing worktree and return its branch.

    Rejects: a symlink, a worktree of another repository ("The task worktree
    belongs to another repository."), and a detached HEAD ("The task worktree
    has no checked-out branch. Switch to a branch before reopening it.").
    """
    if not task.source.exists() and not task.source.is_symlink():
        return None
    info = _validated_worktree(project, task)
    if info.branch is None:
        raise XEnvError(
            "The task worktree has no checked-out branch. Switch to a branch before reopening it."
        )
    return Current(info.branch)


def _copy_local_files(clone: Path, worktree: Path) -> None:
    """Copy git-ignored and `.worktreeinclude` files from the clone.

    For each relative path from `_git.local_files(clone)`:
      - skip if the source is a symlink or not a regular file (log it);
      - skip if the target exists (or is a symlink): never overwrite;
      - reject if any parent folder of the target is a symlink;
      - skip if the path is tracked in the task (log "tracked in the task"),
        so a file deleted in the task is not brought back;
      - copy with metadata to `<dir>/.x-env-copy-<random>`, then publish it
        with `os.link(temp, target)` and remove the temp. `link` fails when the
        target exists, so a file that appeared since the check is never
        overwritten (skip it).
    Running it again copies only files that are new in the clone.
    """
    for relative in _git.local_files(clone):
        source = clone / relative
        target = worktree / relative
        if source.is_symlink() or not source.is_file():
            log.info("Skipping local file that is not a regular file: %s", relative)
            continue
        if target.exists() or target.is_symlink():
            continue
        for parent in _parents_below(worktree, target):
            if parent.is_symlink():
                raise XEnvError(f"Local file destination contains a symbolic link: {parent}")
        if _git.is_tracked(worktree, relative):
            log.info("Skipping local file tracked in the task: %s", relative)
            continue
        if _publish_copy(source, target, relative):
            log.info("Copied local file: %s", relative)


def _parents_below(top: Path, path: Path) -> list[Path]:
    """The folders between `top` (excluded) and `path` (excluded)."""
    return [p for p in path.parents if p != top and p.is_relative_to(top)]


def _publish_copy(source: Path, target: Path, relative: str) -> bool:
    """Copy `source` to `target` without ever overwriting. False if the
    target appeared meanwhile."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.parent / f".x-env-copy-{secrets.token_hex(4)}"
    try:
        shutil.copy2(source, temporary)
        os.link(temporary, target)
        return True
    except FileExistsError:
        return False
    except OSError as error:
        raise XEnvError(f"Could not copy local file into the task: {relative}") from error
    finally:
        temporary.unlink(missing_ok=True)


def task_agents_md(task: WorktreeTask) -> str:
    """The short task instructions. Pure."""
    return (
        f"# Task {task.name}\n"
        "\n"
        f"- Source worktree: {task.source}\n"
        f"- Session records: {task.records}\n"
        "\n"
        "Only one session edits the source worktree at a time.\n"
    )


# --- Delete ---------------------------------------------------------------------------


StopSessions = Callable[[WorktreeTask], bool]
"""Stops every running session of a task and returns True if it found any.
The CLI passes `sessions.stop_task` for this host."""


@dataclass(frozen=True)
class DeleteFacts:
    """What `delete` observed, before any change. Gathered by `_inspect`."""

    dir_exists: bool
    registered: bool  # `worktree list` has `<task>/repo`
    source_exists: bool
    locked: bool  # read from the registration, even when the source is gone
    detached: bool  # only meaningful when source_exists
    dirty: bool  # uncommitted changes, or untracked files that are not ignored
    changed_local_files: tuple[str, ...]  # copied local files whose bytes differ from the clone's


@dataclass(frozen=True)
class DeletePlan:
    remove_registration: bool
    remove_dir: bool


def decide_delete(facts: DeleteFacts, force: bool) -> DeletePlan:
    """The delete rules. Pure, tested as a table."""
    if facts.locked:
        raise XEnvError("The task worktree is locked. Unlock it before deleting the task.")
    if facts.source_exists and not facts.registered:
        raise XEnvError("The task worktree is not registered at its expected path.")
    if facts.source_exists and not force:
        if facts.detached:
            raise XEnvError(
                "The task worktree is detached, possibly during a rebase. Use --force to discard its worktree state."
            )
        if facts.dirty:
            raise XEnvError(
                "The task has uncommitted or untracked files. Use --force to discard them."
            )
        if facts.changed_local_files:
            raise XEnvError(
                f"The task has changed local files: {', '.join(facts.changed_local_files)}. "
                "Use --force to discard them."
            )
    return DeletePlan(remove_registration=facts.registered, remove_dir=facts.dir_exists)


def delete_task(
    project: Project, name: TaskName, *, force: bool, stop_sessions: StopSessions
) -> None:
    """Remove a task's worktree registration and folder. Keep its branch and
    its records (`sessions/<task>/` is outside the task folder).

    A crash after the registration is removed leaves an unregistered folder
    without a source, which the next `delete` removes.
    """
    task = project.task(name)
    with _project_lock(project):
        _validate_clone(project.clone)
        plan = decide_delete(_inspect(project, task), force)
        try:
            stopped = stop_sessions(task)
        except XEnvError as error:
            raise XEnvError("Could not stop the task's sessions. Task files were preserved.") from error
        if not (plan.remove_registration or plan.remove_dir or stopped):
            raise XEnvError(f"Task not found: {task.dir}")
        if plan.remove_registration:
            try:
                _git.worktree_remove(project.clone, task.source, force=force)
            except _git.GitError as error:
                raise XEnvError(
                    "Could not remove the task worktree. Task files remain. Fix the Git error and retry."
                ) from error
        if plan.remove_dir:
            try:
                shutil.rmtree(task.dir)
            except OSError as error:
                raise XEnvError(
                    f"Could not finish deleting {task.dir}. Retry x-env delete {name}."
                ) from error
    log.info("Deleted task: %s", task.dir)


def _inspect(project: Project, task: WorktreeTask) -> DeleteFacts:
    """Read the facts. Rejects symbolic links and a worktree of another
    repository, even with force."""
    if project.tasks_dir.is_symlink() or not project.tasks_dir.is_dir() or task.dir.is_symlink():
        raise XEnvError(f"Expected a task directory without symbolic links: {task.dir}")
    if task.dir.exists() and not task.dir.is_dir():
        raise XEnvError(f"Expected a task directory: {task.dir}")
    registration = _git.registered_worktrees(project.clone).get(task.source)
    source_exists = task.source.exists() or task.source.is_symlink()
    detached = dirty = False
    changed: tuple[str, ...] = ()
    if source_exists:
        info = _validated_worktree(project, task)
        detached = info.branch is None
        dirty = bool(_git.status_porcelain(task.source, ignored=False))
        changed = _changed_local_files(project.clone, task.source)
    return DeleteFacts(
        dir_exists=task.dir.exists(),
        registered=registration is not None,
        source_exists=source_exists,
        locked=registration is not None and registration.locked,
        detached=detached,
        dirty=dirty,
        changed_local_files=changed,
    )


def _changed_local_files(clone: Path, worktree: Path) -> tuple[str, ...]:
    """Local files of the clone that exist in the worktree as regular files
    with other bytes. Skips what the clone no longer has, and what the task
    tracks (`dirty` already covers it)."""
    changed = []
    for relative in _git.local_files(clone):
        source, target = clone / relative, worktree / relative
        if source.is_symlink() or not source.is_file():
            continue
        if target.is_symlink() or not target.is_file():
            continue
        if source.read_bytes() != target.read_bytes() and not _git.is_tracked(worktree, relative):
            changed.append(relative)
    return tuple(changed)


@contextmanager
def _project_lock(project: Project) -> Iterator[None]:
    """`flock` on `<project>/.x-env.lock` (created once, never removed).
    Serializes setup, `task`, and `delete` in one project, so two agents that
    run x-env at the same time do not race on clones, fetches, or worktree
    registration. A crash releases the lock."""
    descriptor = os.open(project.lock_file, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o644)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


# --- Cloud ----------------------------------------------------------------------------


def open_checkout_task(
    root: Path, project: ProjectName, name: TaskName, checkout: Path
) -> CheckoutTask:
    """Cloud and sandbox: the current checkout is the task. No worktree, no
    branch change. Creates only the records folder. `delete` rejects it.

    Not in step 1.
    """
    raise NotImplementedError


# --- Small file helpers (shared by setup and open_task) -----------------------------


def _reject_symlink(path: Path) -> None:
    if path.is_symlink():
        raise XEnvError(f"Expected a directory, not a symbolic link: {path}")
    if path.exists() and not path.is_dir():
        raise XEnvError(f"Expected a directory: {path}")


def ensure_dir(path: Path) -> Path:
    """mkdir -p, but reject a symlink at `path`."""
    _reject_symlink(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_new_file(path: Path, content: str) -> None:
    """Write `content` to a temp file, then publish it with `os.link`, which
    never overwrites. If `path` exists it must be a regular file, and it is
    left unchanged, also when another writer creates it first."""
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_file():
            raise XEnvError(f"Expected a regular file: {path}")
        return
    temporary = path.parent / f".{path.name}.{secrets.token_hex(4)}.tmp"
    try:
        temporary.write_text(content)
        os.link(temporary, path)
    except FileExistsError:
        pass
    finally:
        temporary.unlink(missing_ok=True)
