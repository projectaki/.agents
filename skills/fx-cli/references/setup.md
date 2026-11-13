# Machine setup

Use this guide when `fx` is missing or its environment is incomplete.
`fx setup` creates a project; it does not install the command.
Install only missing dependencies for the requested workflow. Preserve existing
shell configuration, authentication, and repository changes.

## Locate the implementation

Check `type -a fx` and inspect its help. A valid installation lists `setup`,
`task`, `agent`, and `shell-init`. If it is already correct, reuse it.

In the shared `.agents` checkout, the executable is `tools/fx/fx`. Resolve the
checkout that contains this skill; do not assume `/home/work` exists elsewhere.
The normal location is `$HOME/.agents/tools/fx/fx`.

If the repository is absent, clone it into an unused location:

```bash
git clone https://github.com/projectaki/.agents.git "$HOME/.agents"
```

Run that command only if the destination does not exist. If it already exists,
inspect its origin and contents. Use its actual path or another unused location.
Do not replace an unrelated directory, reset a checkout, or pull over local
changes to complete installation. If repository access fails, report the
access requirement and continue checks that do not depend on the checkout.

Keep all of `tools/fx/`, including `agents/`, templates, Python modules, and
default files. The executable resolves companion files relative to its own
directory. Do not copy or symlink only the executable into a bin directory.
There is no separate build or Python package installation step.

## Check dependencies

Use the machine's existing package manager and official installation guidance.
Do not install every optional CLI by default.

| Dependency | Needed for | Check |
| --- | --- | --- |
| Bash and Git | The executable and repository operations | `bash --version`, `git --version` |
| Python 3.9 or later | Task support and response capture | `python3 --version` |
| Rex | Preferred backend for terminal sessions | `rex --autostart=false whoami --json` |
| Zellij | Fallback backend for terminal sessions | `zellij --version` |
| GitHub CLI | Cloning with `owner/repository` shorthand | `gh --version`, `gh auth status` |
| Selected agent CLI | Launching that adapter | `codex --version` or `claude --version` |

For macOS with Homebrew, the base tools can be installed with
`brew install bash git python`. Install only missing packages. For Linux,
use the distribution's Bash, Git, and Python packages. For Rex, follow the
[Rex documentation](https://www.superlogical.com/rex/docs) and connect to the
machine that holds the project. Install Zellij through
an available package or its official release binary for the machine's operating
system and architecture. If Cargo is already installed,
`cargo install --locked zellij` is another supported option.
See [Zellij installation](https://zellij.dev/documentation/installation).

GitHub shorthand requires authenticated `gh`. Follow
[GitHub CLI installation](https://cli.github.com/) if it is missing.
Use `gh auth login` when authentication is needed. A Git URL or local repository
path avoids this dependency, but private remote URLs still need Git credentials.
Preserve the repository selected by the user when choosing its URL form.

Install only the selected coding agent through its official instructions:
[Codex CLI](https://learn.chatgpt.com/docs/codex/cli) or
[Claude Code setup](https://code.claude.com/docs/en/setup).
Check the installed CLI's help for its login flow. Let the user complete any
interactive account authorization; never request credentials in chat.

Read the selected local adapter and adjacent `README.md` for required CLI
features and model access. Adapter `check` verifies executable availability
only. It does not verify authentication, model access, or a working capture hook.
Do not change adapter models as an installation workaround.

## Load the current shell

Use the absolute executable path from the verified checkout:

```bash
fx_bin="$HOME/.agents/tools/fx/fx"
test -x "$fx_bin" || exit 1
"$fx_bin" --help
fx_shell_init="$("$fx_bin" shell-init)" || exit
eval "$fx_shell_init"
type -a fx
fx --help
```

Replace the path if the checkout is elsewhere. Evaluate output only from the
verified implementation. `shell-init` adds its directory to `PATH` and defines
the `fx` function. The function changes directories after successful setup or
a task command with `--no-attach`.

For command runners, prefer the absolute executable plus explicit working
directories. They may not load interactive shell startup files.

## Configure new interactive terminals

Read the selected shell's startup file first. Add one initialization entry to
`.bashrc` for Bash or `${ZDOTDIR:-$HOME}/.zshrc` for Zsh. Use the actual absolute
checkout path. For the default checkout location, the entry is:

```bash
eval "$("$HOME/.agents/tools/fx/fx" shell-init)"
```

Keep one active entry. Replace an obsolete entry instead of appending another.
Preserve unrelated content. Do not configure both shells unless both are in use.
If the user selected another workspace root, place its `FX_ROOT` export before
this entry. Otherwise retain the default `$HOME/work`.

Reload the integration in the current shell with the verified absolute command.
Open a fresh interactive shell to check persistent loading. A shell started
inside a tool call cannot modify its parent terminal; report when the user's
existing terminal still needs to load the entry. Reload existing terminals
after updates that change shell integration.

## Verify the requested capability

1. Confirm `fx --help` shows the project and agent commands. With integration
   loaded, `type fx` should report a shell function.
2. Check dependencies for the requested operation. Project and task preparation
   with `--no-attach` works without a terminal backend.
3. Check the selected adapter without launching a paid model session:
   `"$HOME/.agents/tools/fx/agents/codex" check`, or the `claude` adapter.
   Substitute the actual installation path.
4. If a project and repository were requested, run setup and task preparation
   sequentially as described in the main skill. Confirm the task's `repo/`
   directory and Git status. Do not create a sample project in the real
   workspace merely to test installation.
5. Report which capability is ready and any remaining authentication or
   interactive-terminal requirement. Availability checks do not prove a live
   agent launch or response capture.

If a task appears stuck after `Task ready`, an old shell function may be
capturing terminal output. Load the current integration in another terminal and
reopen the same task. Do not delete or reset it. Scripts that capture a task
path must use `--no-attach`.
