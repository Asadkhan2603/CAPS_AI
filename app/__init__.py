from pathlib import Path
from pkgutil import extend_path


# Allow `uvicorn app.main:app` to work from the repository root by
# resolving the real application package from `backend/app`.
__path__ = extend_path(__path__, __name__)

_backend_app_dir = Path(__file__).resolve().parent.parent / "backend" / "app"
_backend_app_dir_str = str(_backend_app_dir)

if _backend_app_dir.is_dir() and _backend_app_dir_str not in __path__:
    __path__.append(_backend_app_dir_str)
