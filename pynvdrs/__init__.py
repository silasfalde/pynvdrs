from importlib.metadata import PackageNotFoundError, version

from . import annotation, demographics, paths, text, umgpt

try:
	__version__ = version("pynvdrs")
except PackageNotFoundError:  # pragma: no cover - local source tree fallback
	__version__ = "0.1.0"

__all__ = [
	"__version__",
	"annotation",
	"demographics",
	"paths",
	"text",
	"umgpt",
]
