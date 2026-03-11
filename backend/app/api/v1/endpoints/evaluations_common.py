from typing import Any

from app.core.database import db as core_db


def get_evaluations_db() -> Any:
    from app.api.v1.endpoints import evaluations as evaluations_endpoint_module

    return getattr(evaluations_endpoint_module, "db", core_db)
