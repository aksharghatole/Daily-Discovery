from collections.abc import Generator

from sqlalchemy.orm import Session

from database.db import create_session_local


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for FastAPI endpoints."""

    session_factory = create_session_local()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
