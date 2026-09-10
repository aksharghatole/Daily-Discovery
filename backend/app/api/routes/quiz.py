from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.api.dependencies.auth import get_current_user_optional, resolve_user
from backend.app.dependencies.database import get_db
from backend.app.schemas.quiz import QuizQuestionResponse, QuizSubmissionRequest, QuizSubmissionResponse
from database.repository import Repository
from services.daily_generation_service import DailyGenerationService, application_date
from services.discovery_service import load_local_catalog
from services.preferences_service import PreferencesService
from services.progress_service import ProgressService
from services.quiz_service import QuizService

router = APIRouter()


@router.get(
    "/quiz/today",
    summary="Get the daily quiz",
    description="Return the daily quiz questions for the current day using the persisted discovery set.",
    response_model=list[QuizQuestionResponse],
)
def get_today_quiz(
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
) -> list[QuizQuestionResponse]:
    today = application_date()
    user = resolve_user(db, user)
    candidates = PreferencesService().filter_candidates(user, today, load_local_catalog())
    discoveries = DailyGenerationService(db, candidates=candidates).generate_daily_discovery(
        today,
        categories=PreferencesService().categories_for_date(user, today),
    ).discoveries
    questions = QuizService(db).get_or_generate(today, discoveries)
    return [
        QuizQuestionResponse(
            id=question.id,
            question=question.question,
            options=list(question.options),
            correct_answer=question.correct_answer,
            explanation=question.explanation,
            discovery_id=question.discovery_id,
        )
        for question in questions
    ]


@router.post(
    "/quiz/submit",
    summary="Submit a quiz",
    description="Score the supplied answers without trusting the client to calculate the result.",
    response_model=QuizSubmissionResponse,
)
def submit_quiz(
    payload: QuizSubmissionRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
) -> QuizSubmissionResponse:
    try:
        quiz_date = date.fromisoformat(payload.quiz_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.") from exc

    user = resolve_user(db, user)
    discoveries = DailyGenerationService(db, candidates=load_local_catalog()).generate_daily_discovery(quiz_date).discoveries
    questions = QuizService(db).get_or_generate(quiz_date, discoveries)
    if not questions:
        raise HTTPException(status_code=404, detail="No quiz exists for the requested date.")

    normalized = {
        str(question.id): payload.answers.get(str(question.id), "").upper()
        for question in questions
    }
    score, results = QuizService.score_answers(questions, normalized)
    existing = Repository(db).list_quiz_attempts(user)
    if not any(attempt.date == quiz_date for attempt in existing):
        Repository(db).create_quiz_attempt(user, quiz_date, score, len(questions))
        ProgressService(db).record_quiz(user, score, len(questions))
    db.commit()

    return QuizSubmissionResponse(
        score=score,
        total_questions=len(questions),
        correct_answers=results,
        submitted=True,
    )
