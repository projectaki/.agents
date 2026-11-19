"""The command line: parse, dispatch, print.

Output contract (the shell function and skills rely on it):
  - stdout: only the result a caller captures. `setup` and `task` print one
    absolute folder path; `chief`, `agent`, and `run` print the session id;
    `wait` prints the last-turn.md path; `shell-init` prints shell code;
    `install` prints nothing (its changes are progress).
    `_hook` prints nothing, because Claude reads a hook's stdout.
  - `--host <host>`: the same contract, with the remote command's stdout,
    stderr, and exit status (see `host`).
  - stderr: progress and errors, each line `x-env: <message>`.
  - exit: 0 ok, 1 `XEnvError`, 2 `UsageError` and argument errors. `wait`
    exits with the session's exit code; `_session` with the harness's;
    `_hook` always 0.

Raw strings become domain types here and nowhere else (per
boundary-discipline): `ProjectName(...)`, `TaskName(...)`,
`_git.parse_branch(...)`, `parse_repo_source(...)`, `config.load(...)`.
"""

from __future__ import annotations

import argparse
import functools
import logging
import os
import re
import sys
from collections.abc import Sequence
from pathlib import Path

from . import ENTRY, _git, config as config_module, host as hosts, install, records, sessions, workspace
from .harness import claude, codex
from .model import (
    Access,
    BranchRequest,
    DefaultBranch,
    GitHubRepo,
    GitUrl,
    HarnessName,
    LocalRepo,
    ProjectName,
    RepoSource,
    SessionName,
    StackOnto,
    TaskName,
    UsageError,
    UseBase,
    XEnvError,
    feature_branch,
)

log = logging.getLogger("x_env")
_HARNESSES = [h.value for h in HarnessName]
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
With a global option first (`--project`, `--host`), `$1` is that option, so
the folder is not entered. It calls `x-env` by name, which `install` links
into `~/.local/bin`, so it survives a plugin update."""


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point: parse, then dispatch to one handler."""
    _configure_logging()
    argv = list(sys.argv[1:] if argv is None else argv)
    args = _parser().parse_args(argv)
    try:
        if args.host is not None:
            return _forward(args, argv)
        if args.forwarded:
            os.chdir(Path.home())  # the remote side resolves paths from its home folder
            with hosts.marked_stdout():
                return _dispatch(args)
        return _dispatch(args)
    except UsageError as error:
        print(f"x-env: {error}", file=sys.stderr)
        return 2
    except XEnvError as error:
        print(f"x-env: {error}", file=sys.stderr)
        return 1


def _dispatch(args: argparse.Namespace) -> int:
    return args.handler(args, config_module.load(os.environ, Path.home()))


def _forward(args: argparse.Namespace, argv: Sequence[str]) -> int:
    """Run the command on `--host`, after it parsed here, so a typo fails
    before anything reaches the host."""
    if args.command in ("install", "shell-init"):
        raise UsageError(f"{args.command} acts only on the machine it runs on. Run it on the host itself, without --host.")
    try:
        return hosts.forward(args.host, args.command, _without_host(argv), sys.stdout, sys.stderr)
    except KeyboardInterrupt:
        return 130


def _without_host(argv: Sequence[str]) -> list[str]:
    """`argv` without the global `--host <host>` (or `--host=<host>`). Only
    global options come before the command, and `allow_abbrev=False` means
    no other spelling parses."""
    rest = list(argv)
    kept: list[str] = []
    while rest and rest[0].startswith("-"):
        option = rest.pop(0)
        if option == "--host":
            rest.pop(0)
        elif not option.startswith("--host="):
            kept.append(option)
            if option == "--project":
                kept.append(rest.pop(0))
    return kept + rest


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
    """Commands:

      setup <project> [repository]
      task <name> [--base <branch> | --onto <branch> [--branch <new>]]
      delete <name> [--force]
      chief [--prompt <p>] [session options]
      agent --agent <harness> --name <n> [--prompt <p>] [session options]
      run --headless --agent <harness> --name <n> --prompt <p> [session options]
      wait <session id>
      shell-init
      install                                  (links ~/.local/bin/x-env; edits ~/.bashrc, ~/.profile)
      _session --terminal <name> <record>      (internal: the session runner)
      _hook <harness> <record> <event> [<args>...]  (internal: harness hooks)

    Session options: --task <name> --model <m> --effort <e> --access auto|full.
    Global: --project <name>, --host <host> (a Rex host label or address).
    """
    parser = argparse.ArgumentParser(
        prog="x-env", description="Task environments for the x plugin.", allow_abbrev=False,
    )
    parser.add_argument("--project", action=_Once, help="project name, instead of the current folder")
    parser.add_argument("--host", action=_Once,
                        help="run the command on this machine: a Rex host label or server address")
    parser.add_argument("--forwarded", action="store_true", help=argparse.SUPPRESS)  # set by --host
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
    delete.add_argument("--force", action="store_true", help="discard uncommitted files and changed local files")
    delete.set_defaults(handler=cmd_delete)

    chief = commands.add_parser("chief", help="start the task's lead agent: /x:go in a visible session")
    _session_options(chief)
    chief.set_defaults(handler=cmd_chief)

    agent = commands.add_parser("agent", help="start a visible session; headless if no terminal can show it")
    _session_options(agent, named=True)
    agent.set_defaults(handler=cmd_agent)

    run = commands.add_parser("run", help="start a headless session and print its id")
    run.add_argument("--headless", action="store_true", required=True, help="required: run without a terminal")
    _session_options(run, named=True)
    run.set_defaults(handler=cmd_run)

    wait = commands.add_parser("wait", help="wait for a session to exit; print its last-turn.md path")
    wait.add_argument("session")
    wait.set_defaults(handler=cmd_wait)

    shell_init = commands.add_parser("shell-init", help="print shell code: the x-env function")
    shell_init.set_defaults(handler=cmd_shell_init)

    install_command = commands.add_parser("install", help="make x-env a command on this machine")
    install_command.set_defaults(handler=cmd_install)

    runner = commands.add_parser("_session")
    runner.add_argument("--terminal", required=True)
    runner.add_argument("record")
    runner.set_defaults(handler=cmd_session)

    hook = commands.add_parser("_hook")
    hook.add_argument("harness")
    hook.add_argument("record")
    hook.add_argument("event")
    hook.add_argument("payload", nargs="*", help="arguments the harness adds, such as Codex's notify JSON")
    hook.set_defaults(handler=cmd_hook)
    return parser


def _session_options(parser: argparse.ArgumentParser, named: bool = False) -> None:
    if named:
        parser.add_argument("--agent", action=_Once, required=True, choices=_HARNESSES)
        parser.add_argument("--name", action=_Once, required=True, help="session name, the <name> in <nnn>-<name>")
    parser.add_argument("--prompt", action=_Once, help="the first message")
    parser.add_argument("--task", action=_Once, help="task name, instead of the current folder")
    parser.add_argument("--model", action=_Once, help="model; default: the harness's default")
    parser.add_argument("--effort", action=_Once, choices=["low", "medium", "high", "xhigh", "max"])
    parser.add_argument("--access", action=_Once, choices=[a.value for a in Access],
                        help="agent access; default: [this] access in the config, else auto")


# --- Handlers for step 1 ------------------------------------------------------------


def cmd_setup(args: argparse.Namespace, cfg: config_module.Config) -> int:
    name = ProjectName(args.project)
    source = parse_repo_source(args.repository, Path.cwd()) if args.repository is not None else None
    project = workspace.setup(cfg.root, name, source)
    print(project.path)
    if not codex.folder_is_trusted(Path.home(), project.clone):
        log.info(
            "Codex does not trust %s yet. Run codex in %s once and accept the trust prompt, "
            "so that visible Codex sessions start without it.", project.clone, project.clone,
        )
    return 0


def cmd_task(args: argparse.Namespace, cfg: config_module.Config) -> int:
    name = TaskName(args.name)
    request = branch_request(name, args.base, args.onto, args.branch)
    project = workspace.find_project(Path.cwd(), cfg.root, _optional_project(args.project))
    task = workspace.open_task(project, name, request)
    claude.trust_folder(Path.home(), task.source)
    print(task.dir)
    return 0


def cmd_delete(args: argparse.Namespace, cfg: config_module.Config) -> int:
    name = TaskName(args.name)
    project = workspace.find_project(Path.cwd(), cfg.root, _optional_project(args.project))
    stop = functools.partial(sessions.stop_task, host=cfg.host)
    workspace.delete_task(project, name, force=args.force, stop_sessions=stop)
    return 0


def cmd_chief(args: argparse.Namespace, cfg: config_module.Config) -> int:
    """A visible session named `chief` on Claude, whose first message is
    `/x:go <prompt>`. Without --prompt it starts with no first message."""
    prompt = f"/x:go {args.prompt}" if args.prompt is not None else None
    return _start(args, cfg, HarnessName.CLAUDE, SessionName("chief"), prompt, headless=False)


def cmd_agent(args: argparse.Namespace, cfg: config_module.Config) -> int:
    return _start(args, cfg, HarnessName(args.agent), SessionName(args.name), args.prompt, headless=False)


def cmd_run(args: argparse.Namespace, cfg: config_module.Config) -> int:
    if args.prompt is None:
        raise UsageError("run --headless needs --prompt.")
    return _start(args, cfg, HarnessName(args.agent), SessionName(args.name), args.prompt, headless=True)


def _start(
    args: argparse.Namespace, cfg: config_module.Config,
    harness: HarnessName, name: SessionName, prompt: str | None, *, headless: bool,
) -> int:
    project = workspace.find_project(Path.cwd(), cfg.root, _optional_project(args.project))
    task = workspace.find_task(project, Path.cwd(), TaskName(args.task) if args.task is not None else None)
    spec = sessions.SessionSpec(
        harness=harness, name=name, prompt=prompt, model=args.model, effort=args.effort,
        access=Access(args.access) if args.access is not None else None, headless=headless,
    )
    record = sessions.start(task, spec, host=cfg.host, default_access=cfg.access)
    print(record.id)
    return 0


def cmd_wait(args: argparse.Namespace, cfg: config_module.Config) -> int:
    project = workspace.find_project(Path.cwd(), cfg.root, _optional_project(args.project))
    record = records.find(project.sessions_dir, args.session)
    exit_code = sessions.wait(record, cfg.host)
    if not record.last_turn_path.is_file():
        logging.getLogger("x_env").info("The session ended without a finished turn.")
    print(record.last_turn_path)
    return exit_code


def cmd_session(args: argparse.Namespace, cfg: config_module.Config) -> int:
    return sessions.run(records.SessionRecord(Path(args.record)), args.terminal)


def cmd_hook(args: argparse.Namespace, cfg: config_module.Config) -> int:
    """Always exits 0: for Claude, exit 2 would block the prompt or the stop.
    The adapter reads the payload: Claude's from stdin, Codex's from the last
    argument."""
    record = records.SessionRecord(Path(args.record))
    try:
        harness = HarnessName(args.harness)
    except ValueError:
        return 0
    sessions.on_hook(record, harness, args.event, args.payload, sys.stdin)
    return 0


def cmd_shell_init(args: argparse.Namespace, cfg: config_module.Config) -> int:
    """Prints `SHELL_INIT`. PATH is install's job: a PATH entry for the
    versioned plugin folder would go stale on the next plugin update."""
    print(SHELL_INIT.strip())
    return 0


def cmd_install(args: argparse.Namespace, cfg: config_module.Config) -> int:
    for change in install.install(Path.home(), ENTRY):
        log.info("%s", change)
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
