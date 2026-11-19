"""`x-env install`: make `x-env` a command on this machine.

The plugin lives in a harness cache folder whose path includes its version,
so the path to the entry script changes on each update. Install points one
stable name at it, `~/.local/bin/x-env`, and makes shells find that name:

  - `~/.local/bin/x-env`: a symbolic link to the entry script that ran
    install. A link that points elsewhere (an older version) is replaced; a
    regular file is never touched.
  - `~/.bashrc`: one marked block that puts `~/.local/bin` on PATH and loads
    the shell function (`x-env shell-init`), for interactive shells.
  - `~/.profile`: `~/.local/bin` on PATH, for login shells that are not
    interactive, such as the ones Rex starts. Added only when no line there
    already does it.

Each step compares the current state with the goal and changes only the
difference, so a second run changes nothing and returns no messages.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from .model import XEnvError

BEGIN = "# >>> x-env >>>"
END = "# <<< x-env <<<"
_ON_PATH = 'case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) PATH="$HOME/.local/bin:$PATH"; export PATH ;; esac'
BASHRC_BLOCK = f"""{BEGIN}
{_ON_PATH}
if command -v x-env >/dev/null 2>&1; then eval "$(x-env shell-init)"; fi
{END}
"""
PROFILE_BLOCK = f"""{BEGIN}
{_ON_PATH}
{END}
"""
_PUTS_LOCAL_BIN_ON_PATH = re.compile(r"^[^#]*\bPATH=.*\.local/bin")


def install(home: Path, entry: Path) -> list[str]:
    """Bring the three files to their goal. Returns one message per change."""
    try:
        changes = [_link(home / ".local" / "bin" / "x-env", entry)]
        changes.append(_ensure_block(home / ".bashrc", BASHRC_BLOCK))
        profile = home / ".profile"
        if not _puts_local_bin_on_path(profile):
            changes.append(_ensure_block(profile, PROFILE_BLOCK))
    except OSError as error:
        raise XEnvError(f"Install failed: {error}") from error
    return [change for change in changes if change]


def _link(link: Path, entry: Path) -> str | None:
    if link.is_symlink():
        old = os.readlink(link)
        if old == str(entry):
            return None
        _replace_link(link, entry)
        return f"Pointed {link} at {entry} (was {old})."
    if link.exists():
        raise XEnvError(f"{link} exists and is not a symbolic link; x-env left it alone. "
                        "Move it away and run install again.")
    link.parent.mkdir(parents=True, exist_ok=True)
    _replace_link(link, entry)
    return f"Linked {link} to {entry}."


def _replace_link(link: Path, entry: Path) -> None:
    """Create the link under a temporary name, then rename it into place, so
    `x-env` never disappears. A temporary link that a crash left is stale:
    it is removed first."""
    temporary = link.with_name(f".{link.name}.install")
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(entry)
    os.replace(temporary, link)


def _ensure_block(path: Path, block: str) -> str | None:
    """Append the block, or replace an older version of it in place. Writes
    through a symbolic link (dotfile managers link these files)."""
    text = _read(path)
    begin = text.find(BEGIN)
    if begin == -1:
        separator = "" if not text or text.endswith("\n") else "\n"
        with path.open("a") as file:
            file.write(f"{separator}\n{block}" if text else block)
        return f"Added the x-env block to {path}. New shells will have x-env."
    end = text.find(END, begin)
    if end == -1:
        raise XEnvError(f"{path} has the line {BEGIN!r} without {END!r}. Fix or remove the block, "
                        "then run install again.")
    end += len(END) + (1 if text[end + len(END):].startswith("\n") else 0)
    if text[begin:end] == block:
        return None
    path.write_text(text[:begin] + block + text[end:])
    return f"Updated the x-env block in {path}."


def _puts_local_bin_on_path(path: Path) -> bool:
    return any(_PUTS_LOCAL_BIN_ON_PATH.match(line) for line in _read(path).splitlines())


def _read(path: Path) -> str:
    try:
        return path.read_text()
    except FileNotFoundError:
        return ""
