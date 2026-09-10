from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.api.dependencies.auth import get_current_user_optional, resolve_user
from backend.app.dependencies.database import get_db
from backend.app.schemas.search import SearchResponse
from database.repository import Repository
from services.search_service import SearchService

router = APIRouter()


@router.get(
    "/search",
    summary="Search discoveries",
    description="Search discovery titles, content, descriptions, categories, and source names.",
    response_model=SearchResponse,
)
def search_discovers(
    q: str = Query(default="", alias="q"),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
) -> SearchResponse:
    repository = Repository(db)
    user = resolve_user(db, user)
    results = SearchService(db).search(q, user=user)
    items = results[offset : offset + limit]
    return SearchResponse(
        query=q,
        items=[
            {
                "id": item.discovery.id,
                "title": item.discovery.title,
                "category": item.category,
                "date": item.date,
                "source_name": item.source_name,
            }
            for item in items
        ],
        total=len(results),
        limit=limit,
        offset=offset,
    )
