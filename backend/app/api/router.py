from fastapi import APIRouter

from backend.app.api.routes import (
    auth,
    discoveries,
    favorites,
    health,
    history,
    quiz,
    recommendations,
    search,
    settings,
    statistics,
)

router = APIRouter()
router.include_router(auth.router, prefix="/api", tags=["auth"])
router.include_router(health.router, prefix="/api", tags=["health"])
router.include_router(discoveries.router, prefix="/api", tags=["discoveries"])
router.include_router(favorites.router, prefix="/api", tags=["favorites"])
router.include_router(history.router, prefix="/api", tags=["history"])
router.include_router(quiz.router, prefix="/api", tags=["quiz"])
router.include_router(statistics.router, prefix="/api", tags=["statistics"])
router.include_router(recommendations.router, prefix="/api", tags=["recommendations"])
router.include_router(search.router, prefix="/api", tags=["search"])
router.include_router(settings.router, prefix="/api", tags=["settings"])
