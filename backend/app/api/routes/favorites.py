from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.api.dependencies.auth import get_current_user_optional
from backend.app.dependencies.database import get_db
from backend.app.schemas.discovery import DiscoveryListResponse, DiscoveryResponse, FavoritePayload
from database.models import Discovery, User
from database.repository import Repository

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


def _resolve_favorite_user(db: Session, user: User | None = None) -> User:
    if user is not None:
        return user
    return Repository(db).get_or_create_local_user()


@router.post(
    "/discoveries/{discovery_id}/favorite",
    summary="Toggle favorite state for a discovery",
    description="Set a discovery as favorite for the current auth user, or the legacy local user when no token is provided.",
    response_model=FavoritePayload,
)
def set_favorite(
    discovery_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> FavoritePayload:
    resolved_user = _resolve_favorite_user(db, user)
    repository = Repository(db)
    discovery = db.get(__import__('database.models', fromlist=['Discovery']).Discovery, discovery_id)
    if discovery is None:
        raise HTTPException(status_code=404, detail="Discovery not found")
    interaction = repository.set_favorite(resolved_user, discovery, True)
    db.commit()
    return FavoritePayload(discovery_id=discovery.id, favorite=interaction.favorite, user_id=resolved_user.id)


@router.delete(
    "/discoveries/{discovery_id}/favorite",
    summary="Remove a favorite",
    description="Remove the current auth user's or local legacy user's favorite flag for the discovery.",
    response_model=FavoritePayload,
)
def unset_favorite(
    discovery_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> FavoritePayload:
    resolved_user = _resolve_favorite_user(db, user)
    repository = Repository(db)
    discovery = db.get(__import__('database.models', fromlist=['Discovery']).Discovery, discovery_id)
    if discovery is None:
        raise HTTPException(status_code=404, detail="Discovery not found")
    interaction = repository.set_favorite(resolved_user, discovery, False)
    db.commit()
    return FavoritePayload(discovery_id=discovery.id, favorite=interaction.favorite, user_id=resolved_user.id)


@router.get(
    "/favorites",
    summary="See favorite discoveries",
    description="Return the current auth user's favorite discoveries, or the local legacy user when no token is provided.",
    response_model=DiscoveryListResponse,
)
def list_favorites(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> DiscoveryListResponse:
    repository = Repository(db)
    resolved_user = _resolve_favorite_user(db, user)
    items = repository.list_favorites(resolved_user)
    paged = items[offset: offset + limit]
    return DiscoveryListResponse(
        items=[_to_response(item) for item in paged],
        total=len(items),
        limit=limit,
        offset=offset,
    )
