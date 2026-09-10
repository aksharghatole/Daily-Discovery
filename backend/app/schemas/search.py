from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class SearchItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    category: str
    date: date
    source_name: str | None = None


class SearchResponse(BaseModel):
    query: str
    items: list[SearchItem]
    total: int
    limit: int
    offset: int
