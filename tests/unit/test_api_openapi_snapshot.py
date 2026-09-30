"""CI snapshot verification for exported OpenAPI specification."""
from __future__ import annotations

import json
from pathlib import Path

from crowdsight.service.api.app import create_app


def test_openapi_matches_exported_snapshot() -> None:
    app = create_app()
    current_schema = app.openapi()

    repo_root = Path(__file__).resolve().parents[2]
    snapshot_path = repo_root / "contracts" / "app-v1" / "openapi.json"

    assert snapshot_path.is_file(), (
        f"OpenAPI snapshot file missing at {snapshot_path}. "
        "Run `python scripts/export_openapi.py` to generate it."
    )

    saved_schema = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert current_schema == saved_schema, (
        "OpenAPI schema has drifted from exported snapshot in contracts/app-v1/openapi.json! "
        "Run `python scripts/export_openapi.py` to synchronize."
    )
