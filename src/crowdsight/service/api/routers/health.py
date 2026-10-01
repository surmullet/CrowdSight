"""Health check, liveness, and readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from crowdsight.service.api.deps import get_db

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness probe")
def liveness() -> dict[str, str]:
    return {"status": "ok", "service": "crowdsight"}


@router.get("/health/ready", summary="Readiness probe")
def readiness(db: Session = Depends(get_db)) -> dict[str, str]:
    # Check database connectivity
    db.execute(text("SELECT 1"))
    return {"status": "ready", "database": "connected"}
