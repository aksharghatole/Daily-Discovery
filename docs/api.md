# Daily Discovery API

## Base URL

When running locally with Uvicorn:

- http://localhost:8000

## OpenAPI

FastAPI exposes the interactive API docs here:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Endpoints

### Health

- GET /api/health
- Response: {"status": "ok"}

### Discoveries

- GET /api/discoveries/today
- GET /api/discoveries/{date}
- GET /api/discoveries
- GET /api/discoveries/{id}

Query parameters:

- date: ISO date string
- category: optional category filter
- limit: pagination limit, max 50
- offset: pagination offset

### Favorites

- POST /api/discoveries/{id}/favorite
- DELETE /api/discoveries/{id}/favorite
- GET /api/favorites

### History

- GET /api/history

### Quiz

- GET /api/quiz/today
- POST /api/quiz/submit

### Statistics

- GET /api/statistics

### Recommendations

- GET /api/recommendations

### Search

- GET /api/search?q=

### Settings

- GET /api/settings
- PUT /api/settings

## Temporary assumptions

This Phase 1 backend uses the existing single local user behavior from the Streamlit application. It does not yet implement authentication or multi-user accounts.

## Error behavior

- 400: bad request or invalid date
- 404: resource not found
- 422: validation error
- 500: unexpected server error

Internal stack traces are not exposed to clients.

## Local development

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Streamlit remains available via:

```bash
streamlit run app.py
```
