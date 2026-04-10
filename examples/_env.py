"""Helpers for loading local `.env` files in examples."""

from __future__ import annotations

import os
from pathlib import Path


def load_project_dotenv() -> Path | None:
    """Load the repository root `.env` file into `os.environ`.

    Existing environment variables are preserved so shell-provided values still
    take precedence over file-based defaults.

    Returns:
        The loaded `.env` path, or `None` when no repository `.env` exists.
    """
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return None

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        env_key = key.strip()
        env_value = value.strip()

        if not env_key:
            continue

        if (
            len(env_value) >= 2
            and env_value[0] == env_value[-1]
            and env_value[0] in {'"', "'"}
        ):
            env_value = env_value[1:-1]

        os.environ.setdefault(env_key, env_value)

    return env_path
