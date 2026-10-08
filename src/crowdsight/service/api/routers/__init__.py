from crowdsight.service.api.routers.analytics import router as analytics_router
from crowdsight.service.api.routers.artifacts import router as artifacts_router
from crowdsight.service.api.routers.auth import router as auth_router
from crowdsight.service.api.routers.frames import router as frames_router
from crowdsight.service.api.routers.health import router as health_router
from crowdsight.service.api.routers.media import router as media_router
from crowdsight.service.api.routers.model import router as model_router
from crowdsight.service.api.routers.sessions import router as sessions_router
from crowdsight.service.api.routers.zone_sets import router as zone_sets_router

__all__ = [
    "analytics_router",
    "artifacts_router",
    "auth_router",
    "frames_router",
    "health_router",
    "media_router",
    "model_router",
    "sessions_router",
    "zone_sets_router",
]

