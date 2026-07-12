"""Path display and resolution helpers shared across location_platform modules.

These are pure, side-effect-free functions with no filesystem access and no
hidden dependency on the caller's current working directory — callers must
pass any root path explicitly.
"""

from __future__ import annotations

from pathlib import Path


def display_path(path: Path) -> str:
    """Return a POSIX-style path string suitable for messages/output."""
    return path.as_posix()


def resolve_path(value: str, project_root: Path) -> Path:
    """Resolve a possibly-relative path string against ``project_root``.

    Absolute inputs are returned resolved as-is; relative inputs are resolved
    relative to ``project_root``.
    """
    path = Path(value)
    return path.resolve() if path.is_absolute() else (project_root / path).resolve()


def display_relative_path(path: Path, project_root: Path) -> str:
    """Repo-relative POSIX-style path for messages/reports, falling back to str(path).

    Unlike ``display_path``, this formats a path relative to a given project
    root (falling back to ``str(path)`` when ``path`` is not under
    ``project_root``) rather than just POSIX-ifying an already-relative path.
    """
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return str(path)
