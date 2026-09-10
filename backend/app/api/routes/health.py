from fastapi import APIRouter
from sqlalchemy import text

from backend.app.dependencies.database import get_db

router = APIRouter()


@router.get(
    "/health",
    summary="Health check",
    description="Return a minimal status for the backend service itself.",
)
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get(
    "/health/database",
    summary="Database health check",
    description="Confirm that the configured database is reachable without exposing internal credentials.",
)
def database_health() -> dict[str, str]:
    db = next(get_db())
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "available"}
    except Exception:
        return {"status": "error", "database": "unavailable"}
    finally:
        db.close()
