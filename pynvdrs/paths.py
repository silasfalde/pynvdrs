from pathlib import Path
import os
from typing import Optional

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None


def find_project_root(start_path: Optional[str | Path] = None) -> Path:
    """Find repository root by walking up until `requirements.txt` or `pyproject.toml` exists.

    Returns the first parent that looks like a project root. If none found, returns the
    starting path resolved.
    """
    if start_path is None:
        p = Path(__file__).resolve().parent
    else:
        p = Path(start_path).resolve()

    for candidate in [p] + list(p.parents):
        if (candidate / "requirements.txt").exists() or (candidate / "pyproject.toml").exists():
            return candidate

    return p


def maybe_load_dotenv(project_root: Optional[Path] = None) -> None:
    if load_dotenv is not None:
        root = project_root if project_root is not None else find_project_root()
        load_dotenv(root / ".env")


def path_from_env(env_var: str, default_relative: str, project_root: Optional[Path] = None) -> Path:
    """Resolve a path from environment variable falling back to a project-relative default."""
    value = os.getenv(env_var)
    if value:
        p = Path(value).expanduser()
        return p if p.is_absolute() else (Path(value) if Path(value).is_absolute() else (project_root or find_project_root()) / value)
    return (project_root or find_project_root()) / default_relative


def data_paths(prefix: str = "PR_IFIP", project_root: Optional[Path] = None) -> dict:
    """Return common data directory paths using an optional environment prefix.

    Example: `data_paths(prefix='PR_IFIP')` will look for `PR_IFIP_DATA_DIR` env var.
    """
    root = project_root or find_project_root()
    data_dir = path_from_env(f"{prefix}_DATA_DIR", "data", root)
    raw = path_from_env(f"{prefix}_RAW_DIR", str(data_dir / "raw"), root)
    interim = path_from_env(f"{prefix}_INTERIM_DIR", str(data_dir / "interim"), root)
    processed = path_from_env(f"{prefix}_PROCESSED_DIR", str(data_dir / "processed"), root)
    external = path_from_env(f"{prefix}_EXTERNAL_DIR", str(data_dir / "external"), root)

    return {
        "PROJECT_ROOT": root,
        "DATA_DIR": data_dir,
        "RAW_DIR": raw,
        "INTERIM_DIR": interim,
        "PROCESSED_DIR": processed,
        "EXTERNAL_DIR": external,
    }


def root_path(*parts: str, project_root: Optional[Path] = None) -> Path:
    return (project_root or find_project_root()).joinpath(*parts)
