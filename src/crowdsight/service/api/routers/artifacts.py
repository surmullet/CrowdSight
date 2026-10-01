"""Secure artifact retrieval endpoints with path traversal prevention."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from crowdsight.service.api.deps import get_artifact_store, get_db
from crowdsight.service.artifacts.store import ArtifactStore
from crowdsight.service.storage.models import ArtifactRecord

router = APIRouter(prefix="/api/v1/artifacts", tags=["Artifact Storage"])


@router.get("/{artifact_id}", summary="Download a generated artifact by ID")
def get_artifact(
    artifact_id: str,
    db: Session = Depends(get_db),
    store: ArtifactStore = Depends(get_artifact_store),
) -> FileResponse:
    art = db.get(ArtifactRecord, artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail="Artifact not found")

    try:
        path = store.get_path(art.relpath)
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail="Artifact file missing from storage") from err

    content_type = "application/octet-stream"
    if path.suffix.lower() == ".png":
        content_type = "image/png"
    elif path.suffix.lower() in (".json", ".jsonl"):
        content_type = "application/json"
    elif path.suffix.lower() == ".csv":
        content_type = "text/csv"

    return FileResponse(path=path, media_type=content_type, filename=path.name)
