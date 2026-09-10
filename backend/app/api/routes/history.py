from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.api.dependencies.auth import get_current_user_optional
from backend.app.dependencies.database import get_db
from backend.app.schemas.discovery import DiscoveryListResponse
from database.models import User
from database.repository import Repository


def _resolve_history_user(
    db: Session,
    user: User | None = None,
) -> User:
    if user is not None:
        return user
    return Repository(db).get_or_create_local_user()


router = APIRouter()


@router.get(
    "/history",
    summary="Get learning history",
    description="Return the current authenticated user’s history, or the local legacy user when no token is provided.",
    response_model=DiscoveryListResponse,
)
def get_history(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> DiscoveryListResponse:
    repository = Repository(db)
    resolved_user = _resolve_history_user(db, user)
    history = repository.list_learning_history(resolved_user)
    paged = history[offset : offset + limit]
    return DiscoveryListResponse(
        items=[
            {
                "id": entry.discovery.id,
                "date": entry.discovery.date,
                "category": entry.discovery.category.name,
                "title": entry.discovery.title,
                "subtitle": entry.discovery.subtitle,
                "content": entry.discovery.content,
                "description": entry.discovery.description,
                "image_url": entry.discovery.image_url,
                "source_name": entry.discovery.source.name if entry.discovery.source else None,
                "source_url": entry.discovery.source.url if entry.discovery.source else None,
                "source_date": entry.discovery.source.source_date if entry.discovery.source else None,
            }
            for entry in paged
        ],
        total=len(history),
        limit=limit,
        offset=offset,
    )
