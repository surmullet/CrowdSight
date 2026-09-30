"""Unit tests for QualitySummaryCalculator and DataExporter."""
from __future__ import annotations

import json
from typing import Any

from crowdsight.service.analytics.exports import DataExporter
from crowdsight.service.analytics.summary import QualitySummaryCalculator


def test_quality_summary_calculator() -> None:
    obs: list[dict[str, Any]] = [
        {"quality": "VALID", "reason_code": None, "detections": [{"confidence": 0.45}, {"confidence": 0.88}]},
        {"quality": "PARTIAL", "reason_code": "FRAME_PARTIALLY_OBSERVED", "detections": [{"confidence": 0.32}]},
        {"quality": "UNKNOWN", "reason_code": "FRAME_BLANK", "detections": []},
        {"quality": "STALE", "reason_code": "EVIDENCE_STALE", "detections": []},
    ]
    zone_results: list[dict[str, Any]] = [
        {"zone_id": "zone_1", "availability": "COUNTED", "visible_count": 2},
        {"zone_id": "zone_1", "availability": "COUNTED", "visible_count": 1},
        {"zone_id": "zone_1", "availability": "UNKNOWN", "visible_count": None},
        {"zone_id": "zone_1", "availability": "STALE", "visible_count": None},
    ]

    summary = QualitySummaryCalculator.calculate(
        session_id="sess-001",
        observations=obs,
        zone_results=zone_results,
        zone_ids=["zone_1"],
        duration_s=4.0,
        processing_time_s=0.5,
        synthetic=False,
    )

    assert summary.total_frames == 4
    assert summary.valid_frames == 1
    assert summary.partial_frames == 1
    assert summary.unknown_frames == 1
    assert summary.stale_frames == 1
    assert summary.valid_ratio == 0.25

    # Check reason code distribution
    assert summary.reason_code_distribution.get("FRAME_BLANK") == 1
    assert summary.reason_code_distribution.get("EVIDENCE_STALE") == 1

    # Check zone availability
    z1 = summary.zone_availability["zone_1"]
    assert z1.n_frames == 4
    assert z1.n_counted == 2
    assert z1.availability_ratio == 0.5

    # Check 10-bin score distribution
    assert len(summary.raw_score_distribution) == 10
    total_binned = sum(b.count for b in summary.raw_score_distribution)
    assert total_binned == 3


def test_data_exporter_csv_leaves_uncounted_cells_strictly_empty() -> None:
    session_info = {
        "id": "test-session-123",
        "checkpoint_sha256": "a" * 64,
        "synthetic": False,
    }
    zone_results = [
        {"frame_index": 0, "media_time_s": 0.0, "zone_id": "z1", "availability": "COUNTED", "visible_count": 5},
        {"frame_index": 1, "media_time_s": 0.5, "zone_id": "z1", "availability": "UNKNOWN", "visible_count": None},
        {"frame_index": 2, "media_time_s": 1.0, "zone_id": "z1", "availability": "STALE", "visible_count": None},
        {"frame_index": 3, "media_time_s": 1.5, "zone_id": "z1", "availability": "COUNTED", "visible_count": 0},
    ]

    csv_out = DataExporter.export_csv(session_info, zone_results)
    lines = [ln.strip() for ln in csv_out.splitlines() if ln.strip()]

    # First lines are disclaimer and comments
    assert any("DISCLAIMER" in ln for ln in lines)
    # Check data rows
    data_rows = [ln.split(",") for ln in lines if not ln.startswith("#") and not ln.startswith("frame_index")]
    assert len(data_rows) == 4

    # Frame 0: COUNTED, 5
    assert data_rows[0] == ["0", "0.000", "z1", "COUNTED", "5"]
    # Frame 1: UNKNOWN, empty string "" (NEVER "0" or "None")
    assert data_rows[1] == ["1", "0.500", "z1", "UNKNOWN", ""]
    # Frame 2: STALE, empty string ""
    assert data_rows[2] == ["2", "1.000", "z1", "STALE", ""]
    # Frame 3: COUNTED, 0 (an actual zero observation)
    assert data_rows[3] == ["3", "1.500", "z1", "COUNTED", "0"]


def test_data_exporter_jsonl_manifest_line_and_observations() -> None:
    session_info = {
        "id": "test-session-123",
        "model_profile_id": "crowd_best_local_v2",
        "model_profile_sha256": "b" * 64,
        "checkpoint_sha256": "c" * 64,
        "tracker_config_sha256": None,
        "synthetic": False,
        "applicability_snapshot": {"status": "EXPERIMENTAL_NO_APPROVAL"},
    }
    obs = [
        {"frame_index": 0, "media_time_s": 0.0, "quality": "VALID", "payload_v1": {"detections": []}},
    ]
    zone_results = [
        {"frame_index": 0, "zone_id": "z1", "availability": "COUNTED", "visible_count": 0},
    ]

    generator = DataExporter.export_jsonl(session_info, obs, zone_results)
    lines = list(generator)
    assert len(lines) == 2

    manifest = json.loads(lines[0])
    assert manifest["type"] == "manifest"
    assert manifest["session_id"] == "test-session-123"
    assert "experimental_disclaimer" in manifest
    assert "semantics_doc" in manifest

    rec = json.loads(lines[1])
    assert rec["type"] == "observation"
    assert rec["zone_counts"] == [{"zone_id": "z1", "availability": "COUNTED", "visible_count": 0}]
