"""Tests for zone geometry, containment, and validation."""
from __future__ import annotations

from crowdsight.service.domain.zones import (
    Point2D,
    ZoneDefinition,
    ZonePolygon,
    ZoneSet,
    validate_zone_set,
)


def make_box_zone(zone_id: str, x1: float, y1: float, x2: float, y2: float) -> ZoneDefinition:
    vertices = (
        Point2D(x=x1, y=y1),
        Point2D(x=x2, y=y1),
        Point2D(x=x2, y=y2),
        Point2D(x=x1, y=y2),
    )
    return ZoneDefinition(
        zone_id=zone_id,
        name=f"Zone {zone_id}",
        polygon=ZonePolygon(vertices=vertices),
    )


def test_zone_point_containment() -> None:
    zone = make_box_zone("zone1", 100, 100, 300, 300)
    # Inside
    assert zone.contains_point(200, 200) is True
    # Outside
    assert zone.contains_point(50, 50) is False
    assert zone.contains_point(400, 200) is False
    # On boundary (inclusive)
    assert zone.contains_point(100, 200) is True
    assert zone.contains_point(300, 300) is True


def test_zone_with_blind_region() -> None:
    # Outer box 100..300, blind box inside 150..250
    outer_verts = (
        Point2D(x=100, y=100),
        Point2D(x=300, y=100),
        Point2D(x=300, y=300),
        Point2D(x=100, y=300),
    )
    blind_verts = (
        Point2D(x=150, y=150),
        Point2D(x=250, y=150),
        Point2D(x=250, y=250),
        Point2D(x=150, y=250),
    )
    zone = ZoneDefinition(
        zone_id="zone-blind",
        name="Zone with pillar",
        polygon=ZonePolygon(vertices=outer_verts),
        blind_regions=(ZonePolygon(vertices=blind_verts),),
    )
    # In outer but outside blind -> True
    assert zone.contains_point(120, 120) is True
    # In blind region -> False
    assert zone.contains_point(200, 200) is False
    # Outside outer -> False
    assert zone.contains_point(400, 400) is False


def test_validate_zone_set_valid() -> None:
    z1 = make_box_zone("z1", 10, 10, 100, 100)
    z2 = make_box_zone("z2", 150, 150, 250, 250)
    res = validate_zone_set([z1, z2], image_width=1920, image_height=1080)
    assert res.is_valid is True
    assert len(res.errors) == 0
    assert len(res.warnings) == 0


def test_validate_zone_set_duplicate_ids() -> None:
    z1 = make_box_zone("same_id", 10, 10, 100, 100)
    z2 = make_box_zone("same_id", 150, 150, 250, 250)
    res = validate_zone_set([z1, z2], image_width=1920, image_height=1080)
    assert res.is_valid is False
    assert any("Duplicate zone_id" in err for err in res.errors)


def test_validate_zone_set_out_of_bounds() -> None:
    z1 = make_box_zone("z1", 10, 10, 2000, 100)  # 2000 > 1920
    res = validate_zone_set([z1], image_width=1920, image_height=1080)
    assert res.is_valid is False
    assert any("outside frame bounds" in err for err in res.errors)


def test_validate_zone_set_overlapping_warning() -> None:
    z1 = make_box_zone("z1", 100, 100, 300, 300)
    z2 = make_box_zone("z2", 200, 200, 400, 400)  # overlaps [200, 200]..[300, 300]
    res = validate_zone_set([z1, z2], image_width=1920, image_height=1080)
    assert res.is_valid is True  # overlapping is valid by contract, but flagged
    assert len(res.warnings) > 0
    assert any("overlap" in w for w in res.warnings)


def test_zone_set_sha256_deterministic() -> None:
    z1 = make_box_zone("z1", 10, 10, 100, 100)
    zs1 = ZoneSet(
        zone_set_id="zs-01",
        version=1,
        name="Default Set",
        image_width=1920,
        image_height=1080,
        zones=(z1,),
    )
    zs2 = ZoneSet(
        zone_set_id="zs-01",
        version=1,
        name="Default Set",
        image_width=1920,
        image_height=1080,
        zones=(z1,),
    )
    assert zs1.compute_sha256() == zs2.compute_sha256()
