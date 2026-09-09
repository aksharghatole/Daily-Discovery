"""Behavior-based recommendations without AI or fabricated content."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from database.models import Discovery, User, UserDiscovery


@dataclass(frozen=True)
class Recommendation:
    discovery: Discovery
    reason: str
    score: int


class RecommendationService:
    """Rank unseen persisted discoveries from explicit user behavior."""

    def __init__(self, session: Session):
        self.session = session

    def recommend(self, user: User, limit: int = 5) -> list[Recommendation]:
        interactions = self.session.scalars(
            select(UserDiscovery).where(UserDiscovery.user_id == user.id)
        ).all()
        interaction_by_discovery = {item.discovery_id: item for item in interactions}
        category_scores: dict[str, int] = {}
        for interaction in interactions:
            discovery = interaction.discovery
            score = 3 if interaction.favorite else 1 if interaction.viewed else 0
            category_scores[discovery.category.name] = (
                category_scores.get(discovery.category.name, 0) + score
            )
        for category_name in user.preferred_categories or []:
            category_scores[category_name] = category_scores.get(category_name, 0) + 2

        discoveries = self.session.scalars(
            select(Discovery)
            .options(joinedload(Discovery.category), joinedload(Discovery.source))
            .order_by(Discovery.date.desc(), Discovery.id.desc())
        ).all()
        unseen = [
            discovery
            for discovery in discoveries
            if discovery.id not in interaction_by_discovery
        ]
        if not unseen:
            return []
        ranked = sorted(
            unseen,
            key=lambda discovery: (
                -category_scores.get(discovery.category.name, 0),
                -discovery.date.toordinal(),
                -discovery.id,
            ),
        )
        top_categories = {
            name
            for name, _score in sorted(
                category_scores.items(), key=lambda item: (-item[1], item[0])
            )[:2]
        }
        horizons = [
            discovery
            for discovery in ranked
            if discovery.category.name not in top_categories
        ]
        selected = ranked[: max(1, limit)]
        if horizons and len(selected) >= 2:
            selected[-1] = horizons[0]
        selected_ids = {discovery.id for discovery in selected}
        return [
            Recommendation(
                discovery=discovery,
                reason=(
                    "Expand Your Horizons"
                    if discovery.category.name not in top_categories
                    else f"Because you enjoy {discovery.category.name}"
                ),
                score=category_scores.get(discovery.category.name, 0),
            )
            for discovery in selected
            if discovery.id in selected_ids
        ]