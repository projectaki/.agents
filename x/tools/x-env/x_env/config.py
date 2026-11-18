"""Configuration, parsed once at the boundary into typed values.

Step 1 reads only the root: `X_ENV_ROOT`, default `~/work`.

Later steps add `~/.config/x-env/config.toml` (later wins: defaults, file,
environment):

    [this]                 # facts about the machine this file is on
    host = "vps"           # host label written into records (default: hostname)
    access = "full"        # default agent access here (default: "auto")
    checkout_is_task = false   # true in a cloud sandbox: no worktrees

    [hosts.vps]            # machines this one can forward commands to
    transport = "rex"
    target = "vps"         # the Rex host label for `rex -S`
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class HostConfig:
    label: str
    transport: Literal["rex"]
    target: str


@dataclass(frozen=True)
class Config:
    root: Path


def load(env: Mapping[str, str], home: Path) -> Config:
    """Read and validate. An empty `X_ENV_ROOT` counts as unset."""
    return Config(root=Path(env.get("X_ENV_ROOT") or home / "work"))
