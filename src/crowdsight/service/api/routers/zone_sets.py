"""Zone-set configuration, versioning, and live geometric validation."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from crowdsight.service.api.deps import get_db
from crowdsight.service.domain.zones import (
    Point2D,
    ZoneDefinition,
    ZonePolygon,
    ZoneSet,
    ZoneValidationResult,
    validate_zone_set,
)
from crowdsight.service.storage.models import ZoneSetRecord, ZoneSetVersionRecord

router = APIRouter(prefix="/api/v1/zone-sets", tags=["Zone Configuration"])


class ZoneInput(BaseModel):
    zone_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    vertices: list[list[float]] = Field(min_length=3)
    blind_regions: list[list[list[float]]] = Field(default_factory=list)
    description: str | None = None


class ZoneSetCreateRequest(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    image_width: int = Field(ge=1)
    image_height: int = Field(ge=1)
    zones: list[ZoneInput] = Field(min_length=1)


class ZoneSetVersionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    version: int
    image_width: int
    image_height: int
    polygon_data: dict[str, Any]
    sha256: str


class ZoneSetDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    name: str
    versions: list[ZoneSetVersionResponse]


class ValidationRequest(BaseModel):
    image_width: int = Field(ge=1)
    image_height: int = Field(ge=1)
    zones: list[ZoneInput]


class ValidationResponse(BaseModel):
    is_valid: bool
    errors: list[str]
    warnings: list[str]


def _build_domain_zone_definitions(zones_input: list[ZoneInput]) -> list[ZoneDefinition]:
    zone_defs: list[ZoneDefinition] = []
    for z in zones_input:
        poly_verts = tuple(Point2D(x=p[0], y=p[1]) for p in z.vertices)
        blind_polys = tuple(
            ZonePolygon(vertices=tuple(Point2D(x=p[0], y=p[1]) for p in b))
            for b in z.blind_regions
        )
        zone_defs.append(
            ZoneDefinition(
                zone_id=z.zone_id,
                name=z.name,
                polygon=ZonePolygon(vertices=poly_verts),
                blind_regions=blind_polys,
                description=z.description,
            )
        )
    return zone_defs


@router.post("/validate", response_model=ValidationResponse, summary="Validate zone geometries in real time")
def validate_zones(payload: ValidationRequest) -> ValidationResponse:
    try:
        zone_defs = _build_domain_zone_definitions(payload.zones)
    except Exception as exc:
        return ValidationResponse(is_valid=False, errors=[str(exc)], warnings=[])

    result: ZoneValidationResult = validate_zone_set(
        zone_defs,
        image_width=payload.image_width,
        image_height=payload.image_height,
    )
    return ValidationResponse(
        is_valid=result.is_valid,
        errors=result.errors,
        warnings=result.warnings,
    )


@router.get("", response_model=list[ZoneSetDetailResponse], summary="List all zone sets with version history")
def list_zone_sets(db: Session = Depends(get_db)) -> list[ZoneSetRecord]:
    stmt = select(ZoneSetRecord).order_by(ZoneSetRecord.created_at.desc())
    return list(db.scalars(stmt))


@router.post("", response_model=ZoneSetDetailResponse, summary="Create a new zone set with initial version (v1)")
def create_zone_set(
    payload: ZoneSetCreateRequest,
    db: Session = Depends(get_db),
) -> ZoneSetRecord:
    existing = db.get(ZoneSetRecord, payload.id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Zone set {payload.id} already exists")

    # Validate geometries
    zone_defs = _build_domain_zone_definitions(payload.zones)
    val = validate_zone_set(zone_defs, payload.image_width, payload.image_height)
    if not val.is_valid:
        raise HTTPException(status_code=422, detail={"errors": val.errors, "warnings": val.warnings})

    domain_set = ZoneSet(
        zone_set_id=payload.id,
        version=1,
        name=payload.name,
        image_width=payload.image_width,
        image_height=payload.image_height,
        zones=tuple(zone_defs),
    )
    sha256 = domain_set.compute_sha256()

    zs = ZoneSetRecord(id=payload.id, name=payload.name)
    db.add(zs)
    db.flush()

    zsv = ZoneSetVersionRecord(
        zone_set_id=zs.id,
        version=1,
        image_width=payload.image_width,
        image_height=payload.image_height,
        polygon_data={"zones": [z.model_dump() for z in payload.zones]},
        sha256=sha256,
    )
    db.add(zsv)
    db.flush()
    db.refresh(zs)
    return zs


@router.get("/{zone_set_id}", response_model=ZoneSetDetailResponse, summary="Get zone set by ID")
def get_zone_set(zone_set_id: str, db: Session = Depends(get_db)) -> ZoneSetRecord:
    zs = db.get(ZoneSetRecord, zone_set_id)
    if not zs:
        raise HTTPException(status_code=404, detail="Zone set not found")
    return zs


@router.post("/{zone_set_id}/versions", response_model=ZoneSetVersionResponse, summary="Append a new immutable version")
def create_zone_set_version(
    zone_set_id: str,
    payload: ValidationRequest,
    db: Session = Depends(get_db),
) -> ZoneSetVersionRecord:
    zs = db.get(ZoneSetRecord, zone_set_id)
    if not zs:
        raise HTTPException(status_code=404, detail="Zone set not found")

    zone_defs = _build_domain_zone_definitions(payload.zones)
    val = validate_zone_set(zone_defs, payload.image_width, payload.image_height)
    if not val.is_valid:
        raise HTTPException(status_code=422, detail={"errors": val.errors, "warnings": val.warnings})

    latest_version = max([v.version for v in zs.versions], default=0)
    new_version = latest_version + 1

    domain_set = ZoneSet(
        zone_set_id=zone_set_id,
        version=new_version,
        name=zs.name,
        image_width=payload.image_width,
        image_height=payload.image_height,
        zones=tuple(zone_defs),
    )
    sha256 = domain_set.compute_sha256()

    zsv = ZoneSetVersionRecord(
        zone_set_id=zone_set_id,
        version=new_version,
        image_width=payload.image_width,
        image_height=payload.image_height,
        polygon_data={"zones": [z.model_dump() for z in payload.zones]},
        sha256=sha256,
    )
    db.add(zsv)
    db.flush()
    db.refresh(zsv)
    return zsv
