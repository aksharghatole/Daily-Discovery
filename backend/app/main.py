from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.router import router
from config.settings import get_settings

settings = get_settings()

app = FastAPI(
    title="Daily Discovery API",
    description="Backend API for the Daily Discovery knowledge platform.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"message": "Daily Discovery API"}
