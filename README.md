# Daily Discovery

Discover something new every day.

Daily Discovery is being built as a modular personal knowledge platform. The
project currently contains **Phase 14: themes and preferences**.
The engine, provider layer, and Streamlit dashboard can operate with
source-backed content and a local fallback.

## Project structure

```text
daily-discovery/
├── app.py
├── requirements.txt
├── .env.example
├── config/settings.py
├── database/db.py
├── database/models.py
├── database/repository.py
├── data/seed_data.json
├── services/discovery_service.py
├── services/progress_service.py
├── services/quiz_service.py
├── services/statistics_service.py
├── services/search_service.py
├── services/review_service.py
├── services/rabbit_hole_service.py
├── services/recommendation_service.py
├── services/preferences_service.py
├── providers/base.py
├── providers/http.py
├── providers/wikipedia_provider.py
├── providers/dictionary_provider.py
├── providers/country_provider.py
├── providers/astronomy_provider.py
├── providers/books_provider.py
├── scheduler/
├── ui/dashboard.py
├── ui/discovery_card.py
├── utils/
└── tests/
```

The database layer uses SQLAlchemy and is independent of Streamlit. The schema
includes users, categories, sources, discoveries, user interactions, quiz
questions, quiz attempts, and learning history. Foreign keys, relationships,
indexes, and uniqueness constraints are defined in `database/models.py`.
Persistence operations live in `database/repository.py` and accept a
caller-owned SQLAlchemy session. The default local database is SQLite, while
`DATABASE_URL` allows a later PostgreSQL migration without changing the UI.

The Phase 3 engine in `services/discovery_service.py` validates every
candidate, stores its source, avoids normalized-title duplicates, and commits a
complete collection atomically. Running generation twice for the same date
returns the existing collection rather than creating duplicates. The checked-in
`data/seed_data.json` catalog provides two source-backed candidates for each of
the initial Word, Fact, Country, Animal, Science, Space, History, and Place
categories.

Phase 4 providers use public APIs only: Wikipedia's MediaWiki API, Dictionary
API, REST Countries, NASA APOD, and Open Library. They share a bounded-timeout
HTTP client with transient retries and convert malformed or unavailable
responses into provider errors. Tests use mocked responses and never require
network access. Set `NASA_API_KEY` in `.env` for NASA usage; `DEMO_KEY` is the
local default.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run

### Streamlit (existing app)

```bash
streamlit run app.py
```

### FastAPI backend (Phase 1)

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

The API docs are available at:

- http://localhost:8000/docs
- http://localhost:8000/redoc

See [docs/api.md](docs/api.md) for the endpoint catalog.

### Automatic daily generation (Phase 4)

Run the scheduler as a separate process. It generates at `00:05` in
`APP_TIMEZONE` and uses the database-backed generation lock:

```bash
python -m scheduler
```

Generate or recover a specific date manually:

```bash
python -m backend.scripts.generate_daily --date 2026-09-10
```

Omit `--date` to generate the current date in the configured application
timezone. Re-running a date is idempotent; partial runs retry only missing
categories.

The Phase 5 dashboard generates or loads today's collection, shows the date,
category/source metrics, and renders compact two-column discovery cards with
expandable descriptions and clickable source links.

Phase 6 adds sidebar navigation for Today, Explore, Favorites, and History. The
local profile is created automatically, viewing today's collection records a
learning-history event once per day, favorites persist in `user_discoveries`,
and Explore searches titles, content, descriptions, and categories with
optional date filtering.

Phase 7 adds Quiz navigation. Five deterministic questions are generated from
today's persisted discoveries, stored in `quizzes`, and reused on reload. The
answer key is not shown before submission; completed scores are stored in
`quiz_attempts` with an explanation shown after grading.

Phase 8 adds persistent `user_progress` state. Viewing a collection awards 5
XP and advances the streak once per calendar day; missed days reset the current
streak while preserving the longest streak. Favorites award 5 XP, quiz
completion awards 25 XP, and a perfect quiz adds 50 XP. Seven-day and thirty-day
streak milestones award 100 and 500 XP. Levels currently run from Curious to
Polymath and are calculated by the progress service.

Phase 9 adds Statistics navigation with reusable aggregations for viewed
discoveries, favorites, quiz accuracy, category activity, and monthly learning
history. The Streamlit view renders these as metrics plus Plotly bar, line, and
donut charts, with empty states for new profiles.

Phase 10 adds a dedicated Search view. Search matches discovery titles,
content, descriptions, categories, and source names, with optional category,
date, and favorites-only filters. Results show category/date/source metadata
and reuse the existing source-backed discovery cards.

Phase 11 adds Review navigation with a small spaced-repetition schedule. Viewed
discoveries become due for review, remembered answers expand the interval up to
30 days, and missed answers reset the interval to one day. Review state is
stored per user and discovery in `spaced_reviews`.

Phase 12 adds Rabbit Hole navigation. It follows bounded, main-namespace
Wikipedia links into a shallow topic graph, displays source-backed summaries,
and lets the user promote a related topic to the next root. Provider failures
degrade to a clear unavailable state rather than fabricated connections.

Phase 13 adds For You recommendations. The recommendation service learns from
viewed and favorited categories plus explicit preferred categories, ranks only
unseen source-backed discoveries, and injects an "Expand Your Horizons" result
outside the strongest preferences when data allows. No AI service is required.

Phase 14 adds Settings with daily themes and enabled-category preferences.
Available themes include Science, History, Geography, Technology, Culture, Deep
Dive, and Completely Random. Theme filtering is applied before daily generation,
and the SQLite initializer upgrades existing local users tables with the new
preference columns.

## Test

```bash
pytest -q
```

## Configuration

Copy `.env.example` to `.env` and adjust values as needed:

- `DATABASE_URL`: set to SQLite for local development or PostgreSQL for production-like usage
- `NASA_API_KEY`: NASA API key, defaulting to `DEMO_KEY` locally.
- `POSTGRES_*`: local PostgreSQL development variables when using Docker Compose

Secrets and local database files are excluded by `.gitignore`.

Authentication and account ownership details are documented in
[docs/authentication.md](docs/authentication.md),
[docs/data-ownership.md](docs/data-ownership.md), and
[docs/auth-migration.md](docs/auth-migration.md).

## Database setup

### SQLite (default local development)

```env
DATABASE_URL=sqlite:///./data/daily_discovery.db
```

### PostgreSQL (production-like setup)

```env
DATABASE_URL=postgresql+psycopg://daily_discovery:daily_discovery@localhost:5432/daily_discovery
```

### Alembic migrations

```bash
alembic upgrade head
```

For the initial schema, the repo includes the migration in [alembic/versions/20260910_initial_schema.py](alembic/versions/20260910_initial_schema.py).

## Backup guidance

Before testing a migration locally, back up the SQLite database file:

```bash
cp data/daily_discovery.db data/daily_discovery.db.bak
```

## Next phase

Phase 15 will add automatic scheduling and idempotent daily generation jobs.