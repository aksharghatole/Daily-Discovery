from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.api.dependencies.auth import get_current_user_optional, resolve_user
from backend.app.dependencies.database import get_db
from backend.app.schemas.recommendation import RecommendationResponse
from database.repository import Repository
from services.recommendation_service import RecommendationService

router = APIRouter()


@router.get(
    "/recommendations",
    summary="Get recommendations",
    description="Return personalized recommendations using the current service logic.",
    response_model=list[RecommendationResponse],
)
def get_recommendations(
    limit: int = Query(default=5, ge=1, le=10),
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
) -> list[RecommendationResponse]:
    repository = Repository(db)
    user = resolve_user(db, user)
    recommendations = RecommendationService(db).recommend(user, limit=limit)
    return [
        RecommendationResponse(
            id=item.discovery.id,
            title=item.discovery.title,
            category=item.discovery.category.name,
            reason=item.reason,
            score=item.score,
        )
        for item in recommendations
    ]
