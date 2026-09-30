"""Zone geometry, validation, and spatial containment using Shapely 2."""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field, field_validator
from shapely.geometry import Point, Polygon


class Point2D(BaseModel):
    """2D point in image-space pixel coordinates."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    x: float
    y: float

    @field_validator("x", "y")
    @classmethod
    def validate_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("Coordinate must be finite")
        return v


class ZonePolygon(BaseModel):
    """Polygon defined by an ordered list of vertices in pixel coordinates."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    vertices: tuple[Point2D, ...] = Field(min_length=3)

    def to_coordinates(self) -> list[tuple[float, float]]:
        return [(p.x, p.y) for p in self.vertices]

    def to_shapely(self) -> Polygon:
        coords = self.to_coordinates()
        return Polygon(coords)


class ZoneDefinition(BaseModel):
    """Definition of a single named surveillance zone."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    zone_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    polygon: ZonePolygon
    blind_regions: tuple[ZonePolygon, ...] = Field(default=())
    description: str | None = None

    def contains_point(self, px: float, py: float) -> bool:
        """Test whether pixel coordinate (px, py) lies inside or on the boundary of this zone."""
        poly = self.polygon.to_shapely()
        pt = Point(px, py)
        # Check if inside or on boundary of main polygon
        if not (poly.contains(pt) or poly.touches(pt)):
            return False
        # Check blind regions (if point is inside blind region, it is not observed)
        for blind in self.blind_regions:
            blind_poly = blind.to_shapely()
            if blind_poly.contains(pt) or blind_poly.touches(pt):
                return False
        return True


class ZoneSet(BaseModel):
    """Versioned immutable collection of named zones."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    zone_set_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    name: str = Field(min_length=1)
    image_width: int = Field(ge=1)
    image_height: int = Field(ge=1)
    zones: tuple[ZoneDefinition, ...] = Field(min_length=1)

    @property
    def zone_ids(self) -> set[str]:
        return {z.zone_id for z in self.zones}

    def compute_sha256(self) -> str:
        """Compute deterministic SHA-256 fingerprint of the zone set geometry."""
        serialized = json.dumps(
            {
                "zone_set_id": self.zone_set_id,
                "version": self.version,
                "image_width": self.image_width,
                "image_height": self.image_height,
                "zones": [
                    {
                        "zone_id": z.zone_id,
                        "name": z.name,
                        "vertices": [(p.x, p.y) for p in z.polygon.vertices],
                        "blind_regions": [
                            [(p.x, p.y) for p in b.vertices] for b in z.blind_regions
                        ],
                    }
                    for z in sorted(self.zones, key=lambda item: item.zone_id)
                ],
            },
            sort_keys=True,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass
class ZoneValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_zone_set(
    zones: Sequence[ZoneDefinition],
    image_width: int,
    image_height: int,
    *,
    min_area_px: float = 100.0,
) -> ZoneValidationResult:
    """Validate a set of zones against frame dimensions and geometric rules.

    Checks:
    - Non-empty zone set.
    - Unique zone IDs.
    - Polygon simplicity (no self-intersections), valid area >= min_area_px.
    - Vertices within [0, image_width] x [0, image_height].
    - Blind regions valid and within polygon.
    - Warns on zone overlaps.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not zones:
        errors.append("Zone set must contain at least one zone")
        return ZoneValidationResult(is_valid=False, errors=errors, warnings=warnings)

    seen_ids: set[str] = set()
    shapely_polygons: list[tuple[str, Polygon]] = []

    for z in zones:
        # Check uniqueness
        if z.zone_id in seen_ids:
            errors.append(f"Duplicate zone_id: {z.zone_id!r}")
        seen_ids.add(z.zone_id)

        # Check vertices bounds
        for p in z.polygon.vertices:
            if p.x < 0 or p.x > image_width or p.y < 0 or p.y > image_height:
                errors.append(
                    f"Zone {z.zone_id!r} vertex ({p.x}, {p.y}) lies outside frame "
                    f"bounds [0, {image_width}] x [0, {image_height}]"
                )

        # Check Shapely validity
        coords = z.polygon.to_coordinates()
        poly = Polygon(coords)
        if not poly.is_valid:
            errors.append(f"Zone {z.zone_id!r} polygon is invalid or self-intersecting")
        elif poly.area < min_area_px:
            errors.append(
                f"Zone {z.zone_id!r} area ({poly.area:.1f} px²) is smaller than minimum required ({min_area_px} px²)"
            )
        else:
            shapely_polygons.append((z.zone_id, poly))

        # Check blind regions
        for idx, b in enumerate(z.blind_regions):
            b_poly = Polygon(b.to_coordinates())
            if not b_poly.is_valid:
                errors.append(f"Zone {z.zone_id!r} blind region {idx} is invalid")
            elif not poly.contains(b_poly) and not poly.covers(b_poly):
                warnings.append(f"Zone {z.zone_id!r} blind region {idx} extends outside the zone polygon")

    # Check overlaps between zones
    for i in range(len(shapely_polygons)):
        id_a, poly_a = shapely_polygons[i]
        for j in range(i + 1, len(shapely_polygons)):
            id_b, poly_b = shapely_polygons[j]
            intersection = poly_a.intersection(poly_b)
            if not intersection.is_empty and intersection.area > 1.0:
                warnings.append(
                    f"Zones {id_a!r} and {id_b!r} overlap with area {intersection.area:.1f} px². "
                    "Persons in overlapping regions will be counted in both zones."
                )

    return ZoneValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
