from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_active_user,
)
from backend.app.dependencies.database import get_db
from backend.app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    LogoutRequest,
    PasswordChangeRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPairResponse,
    UserPublicResponse,
)
from database.models import UserSession
from database.repository import Repository

router = APIRouter()


def _password_valid(password: str) -> bool:
    return len(password) >= 8 and any(char.isdigit() for char in password)


def _issue_tokens(repository: Repository, user: object, *, device_name: str | None = None, platform: str | None = None):
    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)
    repository.create_session_for_user(
        user,
        refresh_token=refresh_token,
        device_name=device_name,
        platform=platform,
    )
    return access_token, refresh_token


@router.post(
    "/auth/register",
    status_code=status.HTTP_201_CREATED,
    response_model=AuthResponse,
)
def register_user(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    repository = Repository(db)
    normalized_email = payload.email.strip().lower()
    if repository.get_user_by_email(normalized_email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    if not _password_valid(payload.password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters and include a number.",
        )

    user = repository.create_user(
        email=normalized_email,
        password_hash=repository.password_hasher.hash(payload.password),
        display_name=payload.display_name.strip(),
        timezone_name="UTC",
    )
    db.commit()
    access_token, refresh_token = _issue_tokens(repository, user)
    db.commit()

    return AuthResponse(
        user=UserPublicResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            timezone=user.timezone,
            is_active=user.is_active,
            is_admin=user.is_admin,
        ),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/auth/login", response_model=AuthResponse)
def login_user(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    repository = Repository(db)
    user = repository.get_user_by_email(payload.email.strip().lower())
    if user is None or not repository.verify_password(user, payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    user.last_login_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    access_token, refresh_token = _issue_tokens(repository, user)
    db.commit()

    return AuthResponse(
        user=UserPublicResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            timezone=user.timezone,
            is_active=user.is_active,
            is_admin=user.is_admin,
        ),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/auth/refresh", response_model=TokenPairResponse)
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPairResponse:
    repository = Repository(db)
    token_payload = decode_token(payload.refresh_token)
    if token_payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = int(token_payload["sub"])
    user = repository.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user")

    sessions = db.query(UserSession).filter(UserSession.user_id == user.id, UserSession.revoked_at.is_(None)).all()
    active = False
    for session in sessions:
        try:
            if repository.password_hasher.verify(session.refresh_token_hash, payload.refresh_token):
                active = True
                break
        except Exception:
            continue
    if not active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is not active")

    repository.revoke_session(user, payload.refresh_token)
    access_token = create_access_token(user)
    new_refresh_token = create_refresh_token(user)
    repository.create_session_for_user(user, refresh_token=new_refresh_token)
    db.commit()
    return TokenPairResponse(access_token=access_token, refresh_token=new_refresh_token)


@router.get("/auth/me", response_model=UserPublicResponse)
def current_user_profile(current_user: object = Depends(get_current_active_user)) -> UserPublicResponse:
    return UserPublicResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        timezone=current_user.timezone,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
    )


@router.post("/auth/change-password")
def change_password(
    payload: PasswordChangeRequest,
    current_user: object = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    repository = Repository(db)
    if not repository.verify_password(current_user, payload.current_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")
    if not _password_valid(payload.new_password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters and include a number.",
        )

    repository.update_password(current_user, payload.new_password)
    repository.revoke_session(current_user)
    db.commit()
    return {"detail": "Password updated successfully"}


@router.post("/auth/logout")
def logout_user(
    payload: LogoutRequest,
    current_user: object = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    repository = Repository(db)
    repository.revoke_session(current_user, payload.refresh_token)
    db.commit()
    return {"detail": "Logged out"}
