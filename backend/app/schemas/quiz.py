from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class QuizQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    options: list[str]
    correct_answer: str | None = None
    explanation: str | None = None
    discovery_id: int


class QuizSubmissionRequest(BaseModel):
    quiz_date: str
    answers: dict[str, str] = Field(default_factory=dict)


class QuizSubmissionResponse(BaseModel):
    score: int
    total_questions: int
    correct_answers: list[bool]
    submitted: bool = True
