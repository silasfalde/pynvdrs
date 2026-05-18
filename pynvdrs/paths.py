from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

__all__ = [
    "data_dir",
    "data_paths",
    "external_dir",
    "find_project_root",
    "interim_dir",
    "maybe_load_dotenv",
    "path_from_env",
    "processed_dir",
    "project_root",
    "raw_dir",
    "root_path",
]


def _resolve_start_path(start_path: Optional[str | Path] = None) -> Path:
    if start_path is None:
        return Path(__file__).resolve().parent
    return Path(start_path).resolve()


def project_root(
    start_path: Optional[str | Path] = None,
    markers: Iterable[str] = ("pyproject.toml", "requirements.txt", ".git"),
) -> Path:
    """Return the nearest parent directory that looks like a project root.

    The search begins at ``start_path`` when provided, otherwise from the package
    directory. The first directory containing one of ``markers`` is returned.
    """
    path = _resolve_start_path(start_path)

    for candidate in (path, *path.parents):
        if any((candidate / marker).exists() for marker in markers):
            return candidate

    return path


def find_project_root(start_path: Optional[str | Path] = None) -> Path:
    """Backward-compatible alias for :func:`project_root`."""

    return project_root(start_path=start_path)


def maybe_load_dotenv(project_root: Optional[Path] = None) -> None:
    """Load a local ``.env`` file when ``python-dotenv`` is available."""

    if load_dotenv is None:
        return

    root = project_root if project_root is not None else find_project_root()
    load_dotenv(root / ".env")


def path_from_env(env_var: str, default_relative: str, project_root: Optional[Path] = None) -> Path:
    """Resolve a path from an environment variable or a project-relative default."""

    root = project_root if project_root is not None else find_project_root()
    value = os.getenv(env_var)
    if value:
        path = Path(value).expanduser()
        return path if path.is_absolute() else root / path

    default_path = Path(default_relative)
    return default_path if default_path.is_absolute() else root / default_path


def data_dir(env_var: str = "DATA_DIR", default: str = "data", project_root: Optional[Path] = None) -> Path:
    """Return the configured data directory."""

    return path_from_env(env_var, default, project_root)


def raw_dir(env_var: str = "RAW_DIR", default: str = "data/raw", project_root: Optional[Path] = None) -> Path:
    """Return the raw data directory."""

    return path_from_env(env_var, default, project_root)


def interim_dir(env_var: str = "INTERIM_DIR", default: str = "data/interim", project_root: Optional[Path] = None) -> Path:
    """Return the interim data directory."""

    return path_from_env(env_var, default, project_root)


def processed_dir(env_var: str = "PROCESSED_DIR", default: str = "data/processed", project_root: Optional[Path] = None) -> Path:
    """Return the processed data directory."""

    return path_from_env(env_var, default, project_root)


def external_dir(env_var: str = "EXTERNAL_DIR", default: str = "data/external", project_root: Optional[Path] = None) -> Path:
    """Return the external data directory."""

    return path_from_env(env_var, default, project_root)


def data_paths(prefix: str = "PR_IFIP", project_root: Optional[Path] = None) -> dict[str, Path]:
    """Return common data directory paths using an optional environment prefix.

    Example: `data_paths(prefix='PR_IFIP')` will look for `PR_IFIP_DATA_DIR` env var.
    """

    root = project_root if project_root is not None else find_project_root()
    data = data_dir(f"{prefix}_DATA_DIR", "data", root)
    raw = path_from_env(f"{prefix}_RAW_DIR", str(data / "raw"), root)
    interim = path_from_env(f"{prefix}_INTERIM_DIR", str(data / "interim"), root)
    processed = path_from_env(f"{prefix}_PROCESSED_DIR", str(data / "processed"), root)
    external = path_from_env(f"{prefix}_EXTERNAL_DIR", str(data / "external"), root)

    return {
        "PROJECT_ROOT": root,
        "DATA_DIR": data,
        "RAW_DIR": raw,
        "INTERIM_DIR": interim,
        "PROCESSED_DIR": processed,
        "EXTERNAL_DIR": external,
    }


def root_path(*parts: str, project_root: Optional[Path] = None) -> Path:
    """Return a path inside the project root."""

    root = project_root if project_root is not None else find_project_root()
    return root.joinpath(*parts)
