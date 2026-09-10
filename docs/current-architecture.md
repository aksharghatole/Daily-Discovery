# Daily Discovery - Current Architecture Audit

## 1. Existing folder structure

```text
/workspaces/Daily-Discovery
├── app.py
├── README.md
├── requirements.txt
├── .env.example
├── config/
│   └── settings.py
├── data/
│   └── seed_data.json
├── database/
│   ├── __init__.py
│   ├── db.py
│   ├── models.py
│   └── repository.py
├── providers/
│   ├── __init__.py
│   ├── astronomy_provider.py
│   ├── base.py
│   ├── books_provider.py
│   ├── country_provider.py
│   ├── dictionary_provider.py
│   ├── http.py
│   └── wikipedia_provider.py
├── scheduler/
│   └── __init__.py
├── services/
│   ├── __init__.py
│   ├── discovery_service.py
│   ├── preferences_service.py
│   ├── progress_service.py
│   ├── quiz_service.py
│   ├── rabbit_hole_service.py
│   ├── recommendation_service.py
│   ├── review_service.py
│   ├── search_service.py
│   └── statistics_service.py
├── tests/
│   ├── __init__.py
│   ├── test_app.py
│   ├── test_dashboard.py
│   ├── test_database.py
│   ├── test_preferences.py
│   ├── test_progress.py
│   ├── test_providers.py
│   ├── test_quiz.py
│   ├── test_rabbit_hole.py
│   ├── test_recommendation.py
│   ├── test_review.py
│   ├── test_search.py
│   ├── test_services.py
│   ├── test_settings.py
│   └── test_statistics.py
├── ui/
│   ├── __init__.py
│   ├── dashboard.py
│   └── discovery_card.py
├── utils/
│   └── __init__.py
└── docs/
    └── current-architecture.md
```

## 2. Current architecture

The repository is a single-application Python project centered on a reusable persistence layer and a feature-rich Streamlit UI.

### High-level flow

- `app.py` launches the Streamlit dashboard.
- `ui/dashboard.py` renders the main product experience.
- `database/db.py` owns SQLAlchemy engine/session creation.
- `database/models.py` defines the persisted schema.
- `database/repository.py` provides the database access layer used by services.
- `services/*.py` encapsulate business logic (discovery generation, progress, quiz, search, recommendations, statistics, review, preferences, rabbit hole).
- `providers/*.py` fetch external content and normalize it into a common provider format.
- Local seed data in `data/seed_data.json` is used as a trusted fallback when external provider calls are unavailable or for deterministic local generation.

### Architectural strength

This is already a service-oriented application in spirit, but the system is not yet split into a dedicated backend API and frontend clients. The business rules live in Python services rather than inside Streamlit widgets, which is a good migration foundation.

### Architectural gap

The project is still monolithic by design: a single Python app with a local SQLite database and a UI coupled to the domain logic. There is no FastAPI backend, no auth layer, no API schema layer, no timezone-aware generator job pipeline, and no production database migration tooling.

## 3. Existing features implemented in the current codebase

The codebase already includes the following:

- Streamlit UI with multiple pages/views
- SQLite-backed persistence via SQLAlchemy
- Discovery generation from a seed-backed local catalog
- Daily discovery generation with duplicate protection
- Wikipedia provider
- Dictionary provider
- Country provider
- Astronomy provider
- Books provider
- Favorites tracking
- Learning history tracking
- Search across discovery metadata
- Recommendations based on behavior and preferences
- Statistics aggregation
- Daily quiz generation and grading
- XP and streak logic
- Spaced repetition review schedule
- Rabbit hole topic exploration
- Theme and category preference system
- Source-backed metadata on discoveries
- Unit tests covering the core services

## 4. Existing database schema

The schema is defined in `database/models.py` and includes:

### Core entities

- `User`
  - id
  - created_at
  - timezone
  - daily_notification_enabled
  - preferred_categories
  - enabled_categories
  - daily_theme

- `UserProgress`
  - id
  - user_id
  - xp
  - current_streak
  - longest_streak
  - last_active_date

- `Category`
  - id
  - name
  - description

- `Source`
  - id
  - name
  - url
  - source_date
  - retrieved_at

- `Discovery`
  - id
  - date
  - category_id
  - title
  - normalized_title
  - subtitle
  - content
  - description
  - image_url
  - source_id
  - created_at

### User interaction tables

- `UserDiscovery`
  - id
  - user_id
  - discovery_id
  - viewed
  - favorite
  - completed
  - rating
  - viewed_at

- `LearningHistory`
  - id
  - user_id
  - discovery_id
  - date
  - interaction_type

- `Quiz`
  - id
  - date
  - discovery_id
  - question
  - option_a/b/c/d
  - correct_answer
  - explanation

- `QuizAttempt`
  - id
  - user_id
  - date
  - score
  - total_questions
  - completed_at

- `SpacedReview`
  - id
  - user_id
  - discovery_id
  - last_seen
  - times_correct
  - times_incorrect
  - interval_days
  - next_review_date

### Important constraints and indexing

- Unique discovery constraint: one discovery per date/category/title
- Unique user-discovery interaction rows
- Unique user progress row per user
- Unique spaced review row per user/discovery
- Indexed access for date/category and due review tracking
- JSON columns for user preference state

## 5. Existing providers

Defined in `providers/`:

### `providers/base.py`

Defines the shared provider contract and error types:

- `ProviderError`
- `ProviderUnavailable`
- `ProviderItem`
- `ContentProvider` protocol

### `providers/http.py`

- `JsonHttpClient` with request retries, timeout handling, and validation for HTTP JSON payloads

### `providers/wikipedia_provider.py`

- Fetches article summaries and related titles
- Uses the MediaWiki API structure
- Provides `related_titles()` and validation logic

### `providers/dictionary_provider.py`

- Fetches dictionary definitions, part of speech, and metadata

### `providers/country_provider.py`

- Fetches country metadata through REST Countries

### `providers/astronomy_provider.py`

- Fetches NASA APOD content
- Accepts an optional API key from environment settings

### `providers/books_provider.py`

- Fetches book metadata and cover URLs from Open Library

## 6. Existing scheduler implementation

There is a `scheduler/` package, but it is not yet implemented beyond a package stub.

Current state:

- `scheduler/__init__.py` exists
- no jobs registry
- no scheduled generation runner
- no daily job orchestrator
- no status tracking for generation tasks

This means the repository has the structure for a scheduler layer but not the actual automation flow.

## 7. Existing tests

The project includes a meaningful test suite in `tests/` covering the current feature set.

### Current test coverage includes

- application entrypoint imports
- dashboard helper behavior
- database engine / schema expectations
- repository persistence and filtering
- favorites deduplication and history behavior
- preferences validation
- streak and XP rules
- provider mapping and HTTP retries
- quiz generation and scoring
- rabbit hole graph generation
- recommendation heuristics
- review schedule logic
- search behavior
- generation idempotence and invalid candidate handling
- settings/environment loading
- statistics aggregation

### Baseline verification

The current test suite was run with:

```bash
cd /workspaces/Daily-Discovery && pytest -q
```

Result: 30 passed in 2.84s.

## 8. Problems and technical debt discovered

### 1) No backend API foundation

There is no FastAPI app, route layer, or API schema layer. The app is still monolithic.

### 2) No authentication or user accounts

There is a `User` model but no login/register flow, secure password hashing, or token model. This is a major blocker for synchronized multi-device accounts.

### 3) Scheduler is not implemented

The `scheduler/` package exists but there is no actual daily generation job, status tracking, or idempotent orchestration.

### 4) No Postgres migration strategy

The app exposes `DATABASE_URL` in settings, but no Alembic setup or migration project exists.

### 5) No API layer for business logic

Even though the service layer is already strong, the application cannot be reused by web or Android without an API boundary.

### 6) Legacy UI still owns behavior

`ui/dashboard.py` does a lot of orchestration, including generation, voting, quiz logic, search, and progress updates. This is workable for a prototype but it risks duplication during migration.

### 7) Local-only assumptions remain

The project defaults to SQLite and relies on local behavior. This is fine for local development, but it is not yet production-ready for multi-device synchronization.

### 8) No admin and job monitoring endpoints

The roadmap cites admin and daily generation monitoring, but these are not built yet.

### 9) No API or backend documentation infra

There is no FastAPI OpenAPI setup or service-specific schema documentation yet.

### 10) No security-hardening layer

There is no password hashing, access control, rate limiting, CORS policy, or secret management workflow.

## 9. Recommended migration approach

The migration should proceed in a controlled way that preserves the working Streamlit app.

### Recommendation

1. Preserve the current Streamlit app and the core service layer without deleting or rewriting them.
2. Add a dedicated backend folder and a FastAPI app that adapts the current services rather than duplicating them.
3. Keep the database models, repository, and service logic as the canonical business layer.
4. Implement the API contract first using the existing service methods and data models.
5. Add minimal auth with secure hashing and token-based sessions after the API foundation is stable.
6. Add idempotent daily generation as a scheduler-backed backend capability.
7. Keep SQLite for local development and add PostgreSQL readiness with migration tooling.
8. Only after the API is stable, build web and Android apps against it.

This approach avoids destructive rewrites and respects the existing codebase that is already passing tests.

## 10. Exact files that should change in Phase 1

The following are the most likely Phase 1 touchpoints.

### Must be created or extended for the FastAPI foundation

- `backend/main.py`
- `backend/api/__init__.py`
- `backend/api/routes/__init__.py`
- `backend/api/routes/health.py`
- `backend/api/routes/auth.py`
- `backend/api/routes/discovery.py`
- `backend/api/routes/favorites.py`
- `backend/api/routes/library.py`
- `backend/api/routes/history.py`
- `backend/api/routes/quiz.py`
- `backend/api/routes/statistics.py`
- `backend/api/routes/recommendations.py`
- `backend/api/routes/search.py`
- `backend/api/routes/settings.py`
- `backend/api/schemas/__init__.py`
- `backend/api/schemas/*.py` (auth, discovery, quiz, statistics, settings, etc.)
- `backend/core/config.py` or equivalent settings module
- `backend/db/session.py` or equivalent session dependency module
- `backend/dependencies/auth.py` (or similar)
- `backend/services/` wrappers if API-specific service adapters are needed

### Existing files to reuse, not rewrite

- `database/models.py`
- `database/repository.py`
- `database/db.py`
- `services/discovery_service.py`
- `services/progress_service.py`
- `services/quiz_service.py`
- `services/search_service.py`
- `services/recommendation_service.py`
- `services/review_service.py`
- `services/statistics_service.py`
- `services/preferences_service.py`
- `services/rabbit_hole_service.py`
- `config/settings.py`

### Existing UI files to leave intact for the migration period

- `app.py`
- `ui/dashboard.py`
- `ui/discovery_card.py`

## Status

Phase 0 audit complete. The repository already contains a functioning, feature-rich prototype foundation with passing tests, but it is still a monolithic Streamlit-first project without a backend API or auth architecture.

Phase 1 added a FastAPI backend on top of the existing service layer while preserving the legacy Streamlit application.

Phase 2 modernizes the database layer for PostgreSQL compatibility and keeps the SQLite workflow available for local development. The app continues to use the same SQLAlchemy models and repository layer rather than replacing them with a different abstraction.

The next step is Phase 3 only when signaled with: NEXT.
