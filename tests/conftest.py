"""Shared test fixtures for CrowdSight."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPO_ROOT / "contracts" / "v1" / "fixtures"
SCHEMA_PATH = REPO_ROOT / "contracts" / "v1" / "crowd-frame-observation.schema.json"


@pytest.fixture(scope="session")
def schema_path() -> Path:
    assert SCHEMA_PATH.is_file(), f"Schema file missing at {SCHEMA_PATH}"
    return SCHEMA_PATH


@pytest.fixture(scope="session")
def schema_dict(schema_path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(schema_path.read_text(encoding="utf-8")))


@pytest.fixture(scope="session")
def fixture_valid() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((FIXTURES_DIR / "crowd-frame-observation.valid.json").read_text(encoding="utf-8")))


@pytest.fixture(scope="session")
def fixture_zero() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((FIXTURES_DIR / "crowd-frame-observation.zero.json").read_text(encoding="utf-8")))


@pytest.fixture(scope="session")
def fixture_partial() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((FIXTURES_DIR / "crowd-frame-observation.partial.json").read_text(encoding="utf-8")))


@pytest.fixture(scope="session")
def fixture_unknown() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((FIXTURES_DIR / "crowd-frame-observation.unknown.json").read_text(encoding="utf-8")))


@pytest.fixture(scope="session")
def fixture_stale() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((FIXTURES_DIR / "crowd-frame-observation.stale.json").read_text(encoding="utf-8")))


@pytest.fixture(scope="session")
def fixture_tracked() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((FIXTURES_DIR / "crowd-frame-observation.tracked.json").read_text(encoding="utf-8")))



@pytest.fixture(scope="session")
def all_six_fixtures(
    fixture_valid: dict[str, Any],
    fixture_zero: dict[str, Any],
    fixture_partial: dict[str, Any],
    fixture_unknown: dict[str, Any],
    fixture_stale: dict[str, Any],
    fixture_tracked: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    return [
        ("valid", fixture_valid),
        ("zero", fixture_zero),
        ("partial", fixture_partial),
        ("unknown", fixture_unknown),
        ("stale", fixture_stale),
        ("tracked", fixture_tracked),
    ]
