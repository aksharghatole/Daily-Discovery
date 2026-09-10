# Authentication Migration

The original application used one locally created profile. Phase 3 adds real
accounts without deleting that profile or changing the discovery domain model.

## SQLite compatibility

On startup, the SQLite initializer creates the current tables and adds missing
account columns to an existing `users` table. Legacy rows are normalized with
the reserved email `local@daily-discovery.local`; existing user data is kept.
The migration uses explicit backfills because SQLite does not allow every
server default in `ALTER TABLE ... ADD COLUMN` statements.

Back up the local database before testing migrations:

```bash
cp data/daily_discovery.db data/daily_discovery.db.bak
```

## Compatibility behavior

The Streamlit app continues to use the local profile. FastAPI routes accept a
bearer token and scope user-owned state to that account. Requests without a
token use the local profile temporarily, which preserves existing clients but
should be removed when all clients support account authentication.

## PostgreSQL

For PostgreSQL deployments, use the checked-in Alembic migrations rather than
the SQLite compatibility initializer:

```bash
alembic upgrade head
```