from collections.abc import Generator
from pathlib import Path

import cv2
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from crowdsight.service.api.deps import get_db, get_media_registry
from crowdsight.service.storage.media_registry import MediaRegistry
from crowdsight.service.storage.models import MediaAssetRecord

router = APIRouter(prefix="/api/v1/media", tags=["Media Catalog"])


class MediaAssetResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    display_name: str
    sha256: str
    duration_s: float
    fps: float
    frame_count: int
    width: int
    height: int
    codec: str
    browser_playable: bool


@router.get("", response_model=list[MediaAssetResponse], summary="List registered recorded video assets")
def list_media(
    db: Session = Depends(get_db),
    registry: MediaRegistry = Depends(get_media_registry),
) -> list[MediaAssetRecord]:
    return list(registry.list_media())


@router.get("/{asset_id}", response_model=MediaAssetResponse, summary="Get media asset metadata")
def get_media_asset(
    asset_id: str,
    db: Session = Depends(get_db),
) -> MediaAssetRecord:
    asset = db.get(MediaAssetRecord, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")
    return asset


@router.post("/upload", response_model=MediaAssetResponse, status_code=201, summary="Upload a video file to the server catalog")
async def upload_media(
    request: Request,
    filename: str = Query(..., description="Tên tệp video tải lên"),
    display_name: str | None = Query(None, description="Tên hiển thị trong danh mục"),
    registry: MediaRegistry = Depends(get_media_registry),
) -> MediaAssetRecord:
    ext = Path(filename).suffix.lower()
    if ext not in (".mp4", ".webm", ".avi", ".mov", ".mkv"):
        raise HTTPException(
            status_code=400,
            detail=f"Định dạng video không được hỗ trợ: {ext}. Các định dạng cho phép: .mp4, .webm, .avi, .mov, .mkv",
        )

    safe_name = Path(filename).name
    target_path = registry.media_root / safe_name

    try:
        with target_path.open("wb") as buffer:
            async for chunk in request.stream():
                buffer.write(chunk)
    except Exception as exc:
        if target_path.is_file():
            target_path.unlink()
        raise HTTPException(status_code=500, detail=f"Lỗi khi ghi tệp video lên máy chủ: {exc}") from exc

    try:
        record = registry.register_file(target_path, display_name=display_name or safe_name)
        return record
    except Exception as exc:
        if target_path.is_file():
            target_path.unlink()
        raise HTTPException(status_code=400, detail=f"Không thể đọc thông số video (OpenCV): {exc}") from exc


@router.get("/{asset_id}/stream", summary="Stream video with HTTP 206 Range support")
def stream_media(
    asset_id: str,
    request: Request,
    range_header: str | None = Header(None, alias="Range"),
    registry: MediaRegistry = Depends(get_media_registry),
) -> Response:
    try:
        video_path = registry.get_media_path(asset_id)
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail="Media asset not found") from err

    file_size = video_path.stat().st_size
    content_type = "video/mp4"

    if not range_header:
        # Full content stream
        def iter_full() -> Generator[bytes, None, None]:
            with video_path.open("rb") as f:
                while chunk := f.read(1024 * 1024):
                    yield chunk

        return StreamingResponse(
            iter_full(),
            status_code=200,
            headers={
                "Content-Length": str(file_size),
                "Content-Type": content_type,
                "Accept-Ranges": "bytes",
            },
        )

    # Parse Range: bytes=start-end
    try:
        range_str = range_header.strip().replace("bytes=", "")
        start_str, end_str = range_str.split("-", 1)
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
        end = min(end, file_size - 1)
        if start > end or start >= file_size:
            raise ValueError()
    except Exception:
        return Response(
            status_code=416,
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    chunk_size = (end - start) + 1

    def iter_range() -> Generator[bytes, None, None]:
        with video_path.open("rb") as f:
            f.seek(start)
            bytes_left = chunk_size
            while bytes_left > 0:
                to_read = min(bytes_left, 1024 * 1024)
                data = f.read(to_read)
                if not data:
                    break
                bytes_left -= len(data)
                yield data

    return StreamingResponse(
        iter_range(),
        status_code=206,
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
            "Content-Type": content_type,
        },
    )


@router.get("/{asset_id}/frame", summary="Extract single frame as JPEG for zone calibration")
def get_media_frame(
    asset_id: str,
    frame_index: int = Query(0, ge=0),
    registry: MediaRegistry = Depends(get_media_registry),
) -> Response:
    try:
        video_path = registry.get_media_path(asset_id)
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail="Media asset not found") from err

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise HTTPException(status_code=500, detail="Cannot read video asset")

    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, float(frame_index))
        success, frame = cap.read()
        if not success or frame is None:
            raise HTTPException(status_code=404, detail=f"Frame index {frame_index} not found")

        success, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not success:
            raise HTTPException(status_code=500, detail="Failed to encode frame")

        return Response(content=buffer.tobytes(), media_type="image/jpeg")
    finally:
        cap.release()
