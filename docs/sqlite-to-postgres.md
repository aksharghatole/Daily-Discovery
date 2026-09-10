# SQLite to PostgreSQL migration guide

## 1. Back up the current SQLite database

Before any migration experiment, make a safe backup:

```bash
cp data/daily_discovery.db data/daily_discovery.db.bak
```

## 2. Start PostgreSQL

For local compatibility testing, use Docker Compose:

```bash
docker compose up -d postgres
```

## 3. Configure the database URL

Update `.env` to target PostgreSQL:

```env
DATABASE_URL=postgresql+psycopg://daily_discovery:daily_discovery@localhost:5432/daily_discovery
```

## 4. Run Alembic migrations

```bash
alembic upgrade head
```

## 5. Validate the data

After migration, check that the expected row counts and relationships are present:

```bash
python - <<'PY'
from sqlalchemy import text
from database.db import engine
with engine.connect() as conn:
    for table in ['users', 'discoveries', 'quizzes', 'user_discoveries']:
        total = conn.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar_one()
        print(table, total)
PY
```

## 6. Keep the SQLite backup until the PostgreSQL run is validated

Do not delete the SQLite file until the PostgreSQL-backed application has been verified in the same environment.

## 7. Return to SQLite when needed

Set `DATABASE_URL` back to the SQLite file and rerun the app or tests using the local file database.

## 8. Notes

This repository keeps the SQLite workflow as the default for local development while adding PostgreSQL readiness for production-style deployments. The migration setup is intentionally conservative and does not destroy existing data.
