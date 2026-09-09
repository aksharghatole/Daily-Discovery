"""Deterministic daily quiz generation and scoring."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from database.models import Discovery, Quiz
from database.repository import Repository


@dataclass(frozen=True)
class QuizQuestion:
    id: int
    question: str
    options: tuple[str, str, str, str]
    correct_answer: str
    explanation: str
    discovery_id: int


class QuizService:
    """Create and score a persisted daily quiz without external AI services."""

    def __init__(self, session: Session):
        self.repository = Repository(session)

    def get_or_generate(
        self, quiz_date: date, discoveries: list[Discovery], limit: int = 5
    ) -> list[QuizQuestion]:
        existing = self.repository.list_quizzes(quiz_date)
        if existing:
            return [self._to_question(quiz) for quiz in existing]
        selected = discoveries[: max(1, min(limit, 10))]
        if len(selected) < 2:
            return []
        questions: list[QuizQuestion] = []
        for index, discovery in enumerate(selected):
            distractors = [
                item.content for offset, item in enumerate(selected) if offset != index
            ][:3]
            while len(distractors) < 3:
                distractors.append("This information is not included in today's collection.")
            options = tuple([discovery.content] + distractors[:3])
            rotation = index % 4
            rotated = options[rotation:] + options[:rotation]
            correct_answer = "ABCD"[rotated.index(discovery.content)]
            quiz = self.repository.create_quiz(
                quiz_date,
                discovery,
                f"Which statement best describes {discovery.title}?",
                rotated,
                correct_answer,
                discovery.content,
            )
            questions.append(self._to_question(quiz))
        self.repository.session.commit()
        return questions

    @staticmethod
    def score_answers(
        questions: list[QuizQuestion], answers: dict[int, str]
    ) -> tuple[int, list[bool]]:
        results = [answers.get(question.id) == question.correct_answer for question in questions]
        return sum(results), results

    @staticmethod
    def _to_question(quiz: Quiz) -> QuizQuestion:
        return QuizQuestion(
            id=quiz.id,
            question=quiz.question,
            options=(quiz.option_a, quiz.option_b, quiz.option_c, quiz.option_d),
            correct_answer=quiz.correct_answer,
            explanation=quiz.explanation,
            discovery_id=quiz.discovery_id,
        )