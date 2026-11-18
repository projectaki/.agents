"""x-env: task environments for the x plugin.

Public modules: `workspace` (projects and tasks), `records` (session records),
`sessions` (launch and hooks), `model` (types). Modules that start with `_`
are private to the package.
"""

from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent.parent
"""`<x plugin>/tools/x-env`, the folder that `shell-init` adds to PATH."""

ENTRY = TOOL_DIR / "x-env"
"""The entry script. Runner and hook commands call it by absolute path."""

PLUGIN_DIR = TOOL_DIR.parent.parent
"""The x plugin folder, two levels above the tool. Sessions load it."""
