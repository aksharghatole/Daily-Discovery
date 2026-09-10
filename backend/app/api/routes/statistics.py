from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.dependencies.auth import get_current_user_optional, resolve_user
from backend.app.dependencies.database import get_db
from backend.app.schemas.statistics import StatisticsResponse
from database.repository import Repository
from services.progress_service import ProgressService
from services.statistics_service import StatisticsService

router = APIRouter()


@router.get(
    "/statistics",
    summary="Get learning statistics",
    description="Return the current local user’s progress, activity, and quiz metrics.",
    response_model=StatisticsResponse,
)
def get_statistics(
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
) -> StatisticsResponse:
    repository = Repository(db)
    user = resolve_user(db, user)
    progress = ProgressService(db).snapshot(repository.get_or_create_progress(user))
    stats = StatisticsService(db).snapshot(user)
    return StatisticsResponse(
        total_discoveries=len(repository.list_discoveries()),
        total_favorites=len(repository.list_favorites(user)),
        current_streak=progress.current_streak,
        longest_streak=progress.longest_streak,
        xp=progress.xp,
        level=progress.level,
        quiz_attempts=len(repository.list_quiz_attempts(user)),
        average_quiz_score=(
            sum(attempt.score for attempt in repository.list_quiz_attempts(user))
            / sum(attempt.total_questions for attempt in repository.list_quiz_attempts(user))
            if any(attempt.total_questions for attempt in repository.list_quiz_attempts(user))
            else 0.0
        ),
        category_breakdown=stats.category_counts,
        monthly_activity=stats.monthly_activity,
    )
