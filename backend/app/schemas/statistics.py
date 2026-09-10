from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StatisticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_discoveries: int = 0
    total_favorites: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    xp: int = 0
    level: int = 0
    quiz_attempts: int = 0
    average_quiz_score: float = 0.0
    category_breakdown: dict[str, int] = {}
    monthly_activity: dict[str, int] = {}
