from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.api.dependencies.auth import get_current_user_optional, resolve_user
from backend.app.dependencies.database import get_db
from backend.app.schemas.discovery import DiscoveryListResponse, DiscoveryResponse
from database.repository import Repository
from services.daily_generation_service import DailyGenerationService, GenerationError, application_date
from services.discovery_service import load_local_catalog
from services.preferences_service import PreferencesService

router = APIRouter()


def _to_response(discovery) -> DiscoveryResponse:
    return DiscoveryResponse(
        id=discovery.id,
        date=discovery.date,
        category=discovery.category.name,
        title=discovery.title,
        subtitle=discovery.subtitle,
        content=discovery.content,
        description=discovery.description,
        image_url=discovery.image_url,
        source_name=discovery.source.name if discovery.source else None,
        source_url=discovery.source.url if discovery.source else None,
        source_date=discovery.source.source_date if discovery.source else None,
    )


@router.get(
    "/discoveries/today",
    summary="Get today's discovery set",
    description="Generate or load the active discovery collection for the current date.",
    response_model=list[DiscoveryResponse],
)
def get_today_discoveries(
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
) -> list[DiscoveryResponse]:
    today = application_date()
    user = resolve_user(db, user)
    candidates = load_local_catalog()
    candidates = PreferencesService().filter_candidates(user, today, candidates)
    try:
        result = DailyGenerationService(db, candidates=candidates).generate_daily_discovery(
            today,
            categories=PreferencesService().categories_for_date(user, today),
        )
        discoveries = result.discoveries
    except GenerationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return [_to_response(item) for item in discoveries]


@router.get("/generation/status")
def get_generation_status(
    date_: str | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    discovery_date = application_date()
    if date_:
        try:
            discovery_date = date.fromisoformat(date_)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.") from exc
    run = DailyGenerationService(db).get_status(discovery_date)
    if run is None:
        return {"date": discovery_date, "status": "PENDING", "error_count": 0}
    return {
        "date": run.date,
        "status": run.status,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "error_count": run.error_count,
        "last_error": run.last_error,
    }


@router.get(
    "/discoveries/{discovery_key}",
    summary="Get discoveries by date or by ID",
    description="Dates and IDs are both allowed in the final path segment; the server resolves the type based on the input.",
)
def get_discovery_or_date(
    discovery_key: str,
    db: Session = Depends(get_db),
):
    try:
        parsed_date = date.fromisoformat(discovery_key)
    except ValueError:
        try:
            discovery_id = int(discovery_key)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Use a valid ISO date or discovery ID.") from exc
        from database.models import Discovery

        discovery = db.get(Discovery, discovery_id)
        if discovery is None:
            raise HTTPException(status_code=404, detail="Discovery not found")
        return _to_response(discovery)

    discoveries = Repository(db).list_discoveries(discovery_date=parsed_date)
    return [_to_response(item) for item in discoveries]


@router.get(
    "/discoveries",
    summary="List discoveries with pagination",
    description="List discoveries with optional date/category filtering and throttled pagination.",
    response_model=DiscoveryListResponse,
)
def list_discoveries(
    date_: str | None = Query(default=None, alias="date"),
    category: str | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> DiscoveryListResponse:
    parsed_date = None
    if date_:
        try:
            parsed_date = date.fromisoformat(date_)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.") from exc

    items = Repository(db).list_discoveries(discovery_date=parsed_date, category_name=category)
    paged = items[offset : offset + limit]
    return DiscoveryListResponse(
        items=[_to_response(item) for item in paged],
        total=len(items),
        limit=limit,
        offset=offset,
    )
