from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class SourceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    url: str
    source_date: date | None = None


class DiscoveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    category: str
    title: str
    subtitle: str | None = None
    content: str
    description: str | None = None
    image_url: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    source_date: date | None = None


class DiscoveryListResponse(BaseModel):
    items: list[DiscoveryResponse]
    total: int
    limit: int
    offset: int


class FavoritePayload(BaseModel):
    discovery_id: int
    favorite: bool
    user_id: int | None = None
