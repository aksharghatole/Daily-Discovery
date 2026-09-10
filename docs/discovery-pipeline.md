# Discovery Pipeline

## Current flow before Phase 4

The Streamlit Today view and `GET /api/discoveries/today` both construct a
`DailyDiscoveryService` and call `generate(date)`. The service currently:

1. Loads `data/seed_data.json` into `DiscoveryCandidate` values.
2. Optionally filters those candidates using the signed-in user's preferences.
3. Groups candidates by category and selects one deterministic item per category.
4. Rejects short content and non-HTTP source URLs.
5. Checks normalized titles against all historical discoveries.
6. Creates categories, sources, and discoveries in one transaction.
7. Reuses existing rows for a date, making repeated calls idempotent.

The current catalog contains the initial Word, Fact, Country, Animal, Science,
Space, History, and Place categories. Seed data is the only input to the daily
generator today. The Dictionary, Wikipedia, Countries, NASA, and Open Library
providers are implemented separately and are used by provider-focused features,
but are not yet orchestrated into daily generation. The scheduler package is
currently a placeholder, so generation is request-driven by Streamlit or the
FastAPI route rather than automatic.

Quiz questions are generated after discovery generation when the Quiz view or
quiz API is requested. They are derived from persisted discoveries and stored
by date. A quiz failure does not currently have a separate generation status.

Dates are stored as calendar `date` values. Existing callers use the process'
local `date.today()` and do not yet apply the configured application timezone
at the generation boundary.

## Phase 4 flow

The daily job calls one orchestrator. The orchestrator acquires a
database-backed date lock, reuse complete dates, identify missing categories,
request provider content, validate and deduplicate candidates, fall back to
validated seed data, persist successful items, and record `READY`, `PARTIAL`, or
`FAILED` status. Quiz generation will run only against saved discoveries.

Provider failures are isolated per category. A later retry selects only
missing categories, leaving successful discoveries untouched. The public Today
routes will read the orchestrated result and retain the legacy local-user
compatibility behavior.