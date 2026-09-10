from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.api.dependencies.auth import get_current_user_optional, resolve_user
from backend.app.dependencies.database import get_db
from backend.app.schemas.settings import SettingsResponse, SettingsUpdateRequest
from database.repository import Repository
from services.preferences_service import DEFAULT_CATEGORIES, PreferencesService

router = APIRouter()


@router.get(
    "/settings",
    summary="Get local settings",
    description="Return the current local user’s preference snapshot. This is a temporary single-user development assumption.",
    response_model=SettingsResponse,
)
def get_settings(
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
) -> SettingsResponse:
    repository = Repository(db)
    user = resolve_user(db, user)
    snapshot = PreferencesService().snapshot(user)
    return SettingsResponse(
        theme=snapshot.theme,
        enabled_categories=list(snapshot.enabled_categories),
        timezone=user.timezone,
        daily_notification_enabled=user.daily_notification_enabled,
    )


@router.put(
    "/settings",
    summary="Update local settings",
    description="Persist the current local user’s preference state.",
    response_model=SettingsResponse,
)
def update_settings(
    payload: SettingsUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
) -> SettingsResponse:
    repository = Repository(db)
    user = resolve_user(db, user)
    try:
        PreferencesService().set_preferences(
            user,
            theme=payload.theme,
            enabled_categories=payload.enabled_categories or list(DEFAULT_CATEGORIES),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user.timezone = payload.timezone.strip() or "UTC"
    user.daily_notification_enabled = payload.daily_notification_enabled
    db.commit()

    snapshot = PreferencesService().snapshot(user)
    return SettingsResponse(
        theme=snapshot.theme,
        enabled_categories=list(snapshot.enabled_categories),
        timezone=user.timezone,
        daily_notification_enabled=user.daily_notification_enabled,
    )
