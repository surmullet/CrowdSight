"""FastAPI application factory, lifespan management, and RFC 9457 error handlers."""
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from crowdsight.service.api.deps import get_job_manager, init_service_dependencies
from crowdsight.service.api.errors import APIProblemException, problem_response
from crowdsight.service.api.routers import (
    analytics_router,
    artifacts_router,
    auth_router,
    frames_router,
    health_router,
    media_router,
    model_router,
    sessions_router,
    zone_sets_router,
)

logger = logging.getLogger("crowdsight.api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle."""
    init_service_dependencies()
    job_mgr = get_job_manager()
    recovered = job_mgr.recover_orphaned_jobs()
    if recovered > 0:
        logger.warning("Recovered %d orphaned jobs on service startup", recovered)
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="CrowdSight Application API",
        version="1.0.0",
        description=(
            "Application API for CrowdSight recorded fixed-camera crowd monitoring. "
            "Provides media catalog, zone set versioning, session orchestration, "
            "synchronized playback queries, and relative image-space analytics. "
            "Fail-closed governance: operational alerts remain disabled in experimental views."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Enable CORS for local Vite development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # RFC 9457 Exception Handlers
    @app.exception_handler(APIProblemException)
    async def problem_exception_handler(request: Request, exc: APIProblemException) -> Response:
        return problem_response(
            status_code=exc.problem.status,
            title=exc.problem.title,
            detail=exc.problem.detail,
            code=exc.problem.code,
            request=request,
            user_action_hint=exc.problem.user_action_hint,
            problem_type=exc.problem.type,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
        code_map = {
            404: "NOT_FOUND",
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            409: "CONFLICT",
            422: "UNPROCESSABLE_ENTITY",
            500: "INTERNAL_ERROR",
        }
        code = code_map.get(exc.status_code, "ERROR")
        return problem_response(
            status_code=exc.status_code,
            title="HTTP Request Error",
            detail=str(exc.detail),
            code=code,
            request=request,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> Response:
        errors = [f"{'/'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()]
        return problem_response(
            status_code=422,
            title="Request Validation Error",
            detail="; ".join(errors),
            code="REQUEST_VALIDATION_FAILED",
            request=request,
            user_action_hint="Check request body fields and data types against API specification",
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> Response:
        logger.exception("Unhandled server error: %s", exc)
        return problem_response(
            status_code=500,
            title="Internal Server Error",
            detail=str(exc),
            code="INTERNAL_SERVER_ERROR",
            request=request,
            user_action_hint="Please report this issue to the engineering team",
        )

    # Mount Routers
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(model_router)
    app.include_router(media_router)
    app.include_router(zone_sets_router)
    app.include_router(sessions_router)
    app.include_router(frames_router)
    app.include_router(artifacts_router)
    app.include_router(analytics_router)

    # Mount built frontend if available
    from pathlib import Path
    web_dist = Path(__file__).resolve().parents[4] / "web" / "dist"
    if web_dist.is_dir():
        from fastapi.staticfiles import StaticFiles
        app.mount("/", StaticFiles(directory=str(web_dist), html=True), name="static_web")

    return app


app = create_app()
