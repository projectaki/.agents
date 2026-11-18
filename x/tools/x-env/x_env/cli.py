"""The command line: parse, dispatch, print.

Output contract (the shell function and skills rely on it):
  - stdout: only the result a caller captures. `setup` and `task` print one
    absolute folder path; `shell-init` prints shell code. Nothing else.
  - stderr: progress and errors, each line `x-env: <message>`.
  - exit: 0 ok, 1 `XEnvError`, 2 `UsageError` and argument errors.

Raw strings become domain types here and nowhere else (per
boundary-discipline): `ProjectName(...)`, `TaskName(...)`,
`_git.parse_branch(...)`, `parse_repo_source(...)`, `config.load(...)`.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import shlex
import sys
from collections.abc import Sequence
from pathlib import Path

from . import _git, config as config_module, workspace
from .model import (
    BranchRequest,
    DefaultBranch,
    GitHubRepo,
    GitUrl,
    LocalRepo,
    ProjectName,
    RepoSource,
    StackOnto,
    TaskName,
    UsageError,
    UseBase,
    XEnvError,
    feature_branch,
)

TOOL_DIR = Path(__file__).resolve().parent.parent
_GITHUB_NAME = re.compile(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+")

SHELL_INIT = r"""
x-env() {
  case "${1-}" in
    setup|task)
      local x_env_destination
      x_env_destination="$(command x-env "$@")" || return
      builtin cd -- "$x_env_destination"
      ;;
    *) command x-env "$@" ;;
  esac
}
"""
"""`setup` and `task` print a folder; the function enters it only on success.
With a global option first (`--project`), `$1` is that option, so the folder
is not entered."""


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point: parse, then dispatch to one handler."""
    _configure_logging()
    args = _parser().parse_args(argv)
    try:
        return args.handler(args, config_module.load(os.environ, Path.home()))
    except UsageError as error:
        print(f"x-env: {error}", file=sys.stderr)
        return 2
    except XEnvError as error:
        print(f"x-env: {error}", file=sys.stderr)
        return 1


def _configure_logging() -> None:
    logger = logging.getLogger("x_env")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("x-env: %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False


class _Once(argparse.Action):
    """Store an option's value, and reject the option when it is repeated."""

    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, self.dest) is not None:
            parser.error(f"{option_string} can be given only once")
        setattr(namespace, self.dest, values)


def _parser() -> argparse.ArgumentParser:
    """Commands (step 1):

      setup <project> [repository]
      task <name> [--base <branch> | --onto <branch> [--branch <new>]]
      delete <name> [--force]
      shell-init

    Global: --project <name>.
    """
    parser = argparse.ArgumentParser(prog="x-env", description="Task environments for the x plugin.")
    parser.add_argument("--project", action=_Once, help="project name, instead of the current folder")
    commands = parser.add_subparsers(dest="command", required=True, metavar="command")

    setup = commands.add_parser("setup", help="create a project and clone its repository once")
    setup.add_argument("project")
    setup.add_argument("repository", nargs="?")
    setup.set_defaults(handler=cmd_setup)

    task = commands.add_parser("task", help="create or reopen a task worktree")
    task.add_argument("name")
    task.add_argument("--base", action=_Once, help="work on this branch")
    task.add_argument("--onto", action=_Once, help="start a new branch at this branch")
    task.add_argument("--branch", action=_Once, help="name of the new branch with --onto")
    task.set_defaults(handler=cmd_task)

    delete = commands.add_parser("delete", help="remove a task worktree; keep its branch and records")
    delete.add_argument("name")
    delete.add_argument("--force", action="store_true", help="discard uncommitted and ignored files")
    delete.set_defaults(handler=cmd_delete)

    shell_init = commands.add_parser("shell-init", help="print shell code: PATH and the x-env function")
    shell_init.set_defaults(handler=cmd_shell_init)
    return parser


# --- Handlers for step 1 ------------------------------------------------------------


def cmd_setup(args: argparse.Namespace, cfg: config_module.Config) -> int:
    name = ProjectName(args.project)
    source = parse_repo_source(args.repository, Path.cwd()) if args.repository is not None else None
    project = workspace.setup(cfg.root, name, source)
    print(project.path)
    return 0


def cmd_task(args: argparse.Namespace, cfg: config_module.Config) -> int:
    name = TaskName(args.name)
    request = branch_request(name, args.base, args.onto, args.branch)
    project = workspace.find_project(Path.cwd(), cfg.root, _optional_project(args.project))
    task = workspace.open_task(project, name, request)
    print(task.dir)
    return 0


def cmd_delete(args: argparse.Namespace, cfg: config_module.Config) -> int:
    name = TaskName(args.name)
    project = workspace.find_project(Path.cwd(), cfg.root, _optional_project(args.project))
    workspace.delete_task(project, name, force=args.force, stop_sessions=lambda task: False)
    return 0


def cmd_shell_init(args: argparse.Namespace, cfg: config_module.Config) -> int:
    """Prints a PATH line that adds the tool folder once, and `SHELL_INIT`."""
    directory = shlex.quote(str(TOOL_DIR))
    print(f'case ":$PATH:" in *:{directory}:*) ;; *) export PATH={directory}:"$PATH" ;; esac')
    print(SHELL_INIT.strip())
    return 0


# --- Boundary parsers ---------------------------------------------------------------


def branch_request(
    task: TaskName, base: str | None, onto: str | None, branch: str | None
) -> BranchRequest:
    """The only place that reads `--base`, `--onto`, and `--branch` together."""
    if onto is not None and base is not None:
        raise UsageError("Use --base or --onto, not both. Name the new branch of --onto with --branch.")
    if branch is not None and onto is None:
        raise UsageError("Use --branch only with --onto.")
    if onto is not None:
        return StackOnto(
            start=_git.parse_branch(onto, "onto"),
            new_branch=_git.parse_branch(branch, "branch") if branch is not None else feature_branch(task),
        )
    if base is not None:
        return UseBase(_git.parse_branch(base, "base"))
    return DefaultBranch()


def parse_repo_source(raw: str, cwd: Path) -> RepoSource:
    """An existing folder -> LocalRepo (resolved); `owner/name` -> GitHubRepo;
    anything else -> GitUrl. Rejects a leading `-` and an empty value."""
    if not raw or raw.startswith("-"):
        raise UsageError("Repository must not be empty or start with a dash.")
    path = cwd / raw
    if path.is_dir():
        return LocalRepo(path.resolve())
    if _GITHUB_NAME.fullmatch(raw):
        owner, name = raw.split("/")
        return GitHubRepo(owner, name)
    return GitUrl(raw)


def _optional_project(raw: str | None) -> ProjectName | None:
    return ProjectName(raw) if raw is not None else None


if __name__ == "__main__":
    sys.exit(main())
