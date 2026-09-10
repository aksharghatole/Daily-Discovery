from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    theme: str
    enabled_categories: list[str]
    timezone: str
    daily_notification_enabled: bool


class SettingsUpdateRequest(BaseModel):
    theme: str
    enabled_categories: list[str]
    timezone: str
    daily_notification_enabled: bool
