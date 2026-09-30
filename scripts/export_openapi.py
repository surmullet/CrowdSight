"""Export OpenAPI schema for CrowdSight application layer."""
from __future__ import annotations

import json
from pathlib import Path

from crowdsight.service.api.app import create_app


def export_openapi() -> None:
    app = create_app()
    openapi_schema = app.openapi()

    repo_root = Path(__file__).resolve().parents[1]
    out_dir = repo_root / "contracts" / "app-v1"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / "openapi.json"
    formatted = json.dumps(openapi_schema, indent=2, sort_keys=True)
    out_file.write_text(formatted + "\n", encoding="utf-8")
    print(f"Exported OpenAPI schema to {out_file}")


if __name__ == "__main__":
    export_openapi()
