# Database Architecture

## Current database layer

The project uses SQLAlchemy declarative models and a repository layer that wraps a caller-owned `Session`.

Relevant files:

- [database/db.py](database/db.py)
- [database/models.py](database/models.py)
- [database/repository.py](database/repository.py)
- [config/settings.py](config/settings.py)
- [backend/app/dependencies/database.py](backend/app/dependencies/database.py)

## Database engine and configuration

Database configuration is centralized in [config/settings.py](config/settings.py). The default is SQLite for local development:

```env
DATABASE_URL=sqlite:///./data/daily_discovery.db
```

A PostgreSQL production-style value is also supported:

```env
DATABASE_URL=postgresql+psycopg://username:password@host:5432/database
```

The engine factory in [database/db.py](database/db.py) creates the SQLAlchemy engine based on `DATABASE_URL` and only applies SQLite-specific settings conditionally. PostgreSQL uses the driver-compatible `psycopg` URL, and the engine is otherwise database-agnostic.

## Session management

`SessionLocal` is created from the configured engine and is used by both the Streamlit app and the FastAPI dependency. Sessions are opened and closed through a single reusable factory, which keeps connection handling consistent across the app.

## Core schema

The current schema includes:

- `users`
- `user_progress`
- `categories`
- `sources`
- `discoveries`
- `user_discoveries`
- `quizzes`
- `quiz_attempts`
- `learning_history`
- `spaced_reviews`

The schema uses standard SQLAlchemy portable constructs, and the model definitions are concentrated in [database/models.py](database/models.py).

## SQLite-specific behavior currently present

The current code contains a few SQLite-specific safeguards, but they are limited to connection handling and directory creation for the SQLite file path. These are guarded by prefix checks and are not applied to PostgreSQL connections.

## Database health and compatibility

The API includes a lightweight database health endpoint and the app keeps its SQLite default for local development. PostgreSQL readiness is ensured at the configuration and connection layer, while the schema itself remains compatible with both engines.

## Alembic

Alembic is configured in:

- [alembic.ini](alembic.ini)
- [alembic/env.py](alembic/env.py)

The initial migration is in:

- [alembic/versions/20260910_initial_schema.py](alembic/versions/20260910_initial_schema.py)

## Backup safety

Before changing a database, back up the SQLite file:

```bash
cp data/daily_discovery.db data/daily_discovery.db.bak
```

Keep the backup until PostgreSQL validation is complete.

## Migration notes

This phase does not delete or recreate the existing database. The migration setup is meant to document and support the current schema and preserve the existing local SQLite workflow while adding PostgreSQL compatibility.
