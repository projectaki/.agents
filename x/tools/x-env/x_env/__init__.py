"""x-env: task environments for the x plugin.

Public modules: `workspace` (projects and tasks), `records` (session records),
`sessions` (launch and hooks), `model` (types). Modules that start with `_`
are private to the package.
"""

from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent.parent
"""`<x plugin>/tools/x-env`. Resolved, so it is the versioned folder even
when x-env runs through the `~/.local/bin/x-env` link."""

ENTRY = TOOL_DIR / "x-env"
"""The entry script. Runner and hook commands call it by absolute path, and
`install` links `~/.local/bin/x-env` to it."""
