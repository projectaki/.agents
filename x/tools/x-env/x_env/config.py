"""Configuration, parsed once at the boundary into typed values.

Sources (later wins: defaults, file, environment):

  - `~/.config/x-env/config.toml`, optional:

        [this]                 # facts about the machine this file is on
        host = "vps"           # host label written into records (default: hostname)
        access = "full"        # default agent access here (default: "auto")

  - `X_ENV_ROOT`, default `~/work`. An empty value counts as unset.

Later steps add `[this] checkout_is_task` and `[hosts.<label>]` (transport,
target) for `--host`. Until then, other keys are ignored.
"""

from __future__ import annotations

import socket
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .model import Access, XEnvError


@dataclass(frozen=True)
class HostConfig:
    label: str
    transport: Literal["rex"]
    target: str


@dataclass(frozen=True)
class Config:
    root: Path
    host: str  # this machine's label in records
    access: Access  # the default for sessions started here


def config_file(home: Path) -> Path:
    return home / ".config" / "x-env" / "config.toml"


def load(env: Mapping[str, str], home: Path) -> Config:
    """Read and validate. Raises `XEnvError` naming the file when it is not
    valid TOML or a value has the wrong type."""
    path = config_file(home)
    this = _this_table(path)
    host = this.get("host", socket.gethostname())
    if not isinstance(host, str) or not host:
        raise XEnvError(f"[this] host must be a non-empty string: {path}")
    try:
        access = Access(this.get("access", Access.AUTO))
    except ValueError as error:
        raise XEnvError(f"[this] access must be auto or full: {path}") from error
    return Config(root=Path(env.get("X_ENV_ROOT") or home / "work"), host=host, access=access)


def _this_table(path: Path) -> dict[str, Any]:
    try:
        data = tomllib.loads(path.read_text())
    except FileNotFoundError:
        return {}
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise XEnvError(f"Unreadable config file: {path} ({error})") from error
    this = data.get("this", {})
    if not isinstance(this, dict):
        raise XEnvError(f"[this] must be a table: {path}")
    return this
