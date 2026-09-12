"""Shared run-provenance helpers used by both the connectome build and experiments."""

from __future__ import annotations

import platform
import subprocess
import sys
from datetime import datetime, timezone

import config


def get_git_commit() -> str:
    """Best-effort git commit hash for the current tree; "unknown" if there is no repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=config.PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        return "unknown"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def python_version() -> str:
    return sys.version.split()[0]


def platform_summary() -> str:
    return f"{platform.system()} {platform.release()} ({platform.machine()})"
