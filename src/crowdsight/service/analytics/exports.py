"""Data export utilities for JSONL observation archives and CSV zone counts."""
from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterator, Sequence
from typing import Any

EXPERIMENTAL_EXPORT_DISCLAIMER = (
    "Thử nghiệm — mô hình chưa được duyệt cho vận hành thực tế. "
    "Số người nhìn thấy được, do mô hình phát hiện, trong vùng được quan sát. "
    "Mô hình có thể đếm thiếu ở cảnh đông. Không phải sức chứa hay lượng người tham dự."
)

SEMANTICS_MD_TEXT = """# CrowdSight Data Semantics & Limitations

## Measurement Definition
The numbers presented in this export represent:
**"Số người nhìn thấy được, do mô hình phát hiện, trong vùng được quan sát"**
(Number of visible persons detected by the model within the observed zone).

## Strict Invariants & Prohibitions
1. **Never Capacity or Attendance**: These numbers do NOT represent capacity, attendance, crowd level, safety, or wait times.
2. **Missing Data is Never Zero**: When a zone or frame is not fully observed (`UNKNOWN`, `STALE`, `NOT_FULLY_OBSERVED`), the count is left blank / null. It is NOT zero.
3. **Model Scores**: Confidence scores are uncalibrated raw model scores (`confidence_semantics: RAW_MODEL_SCORE`), NOT calibrated probabilities.
4. **Heat Maps**: Heat maps are strictly relative image-space visualizations (`IMAGE_SPACE`). They are NOT geographic maps or density in people/m².
5. **No Metric Density**: Metric density (`density_people_per_m2`) is UNAVAILABLE pending site-specific calibration.
6. **Experimental Replay Only**: This deployment is experimental (`EXPERIMENTAL_NO_APPROVAL`). Operational alert gates are strictly disabled.
"""


class DataExporter:
    """Exports session data to JSONL or CSV strictly obeying domain invariants."""

    @staticmethod
    def export_jsonl(
        session_info: dict[str, Any],
        observations: Sequence[dict[str, Any]],
        zone_results: Sequence[dict[str, Any]],
    ) -> Iterator[str]:
        """Stream JSONL lines: 1st line manifest, followed by observation records."""
        # Line 1: Manifest with provenance and disclaimers
        manifest = {
            "type": "manifest",
            "session_id": session_info.get("id"),
            "model_profile_id": session_info.get("model_profile_id"),
            "model_profile_sha256": session_info.get("model_profile_sha256"),
            "checkpoint_sha256": session_info.get("checkpoint_sha256"),
            "tracker_config_sha256": session_info.get("tracker_config_sha256"),
            "synthetic": session_info.get("synthetic", False),
            "applicability": session_info.get("applicability_snapshot", {}),
            "experimental_disclaimer": EXPERIMENTAL_EXPORT_DISCLAIMER,
            "semantics_doc": SEMANTICS_MD_TEXT,
        }
        yield json.dumps(manifest, ensure_ascii=False) + "\n"

        # Group zone results by frame_index
        zone_res_by_frame: dict[int, list[dict[str, Any]]] = {}
        for zr in zone_results:
            f_idx = int(zr["frame_index"])
            zone_res_by_frame.setdefault(f_idx, []).append({
                "zone_id": zr["zone_id"],
                "availability": zr["availability"],
                "visible_count": zr.get("visible_count"),
            })

        for obs in observations:
            f_idx = int(obs.get("frame_index", 0))
            record = {
                "type": "observation",
                "observation": obs.get("payload_v1", obs),
                "zone_counts": zone_res_by_frame.get(f_idx, []),
            }
            yield json.dumps(record, ensure_ascii=False) + "\n"

    @staticmethod
    def export_csv(
        session_info: dict[str, Any],
        zone_results: Sequence[dict[str, Any]],
    ) -> str:
        """Generate CSV string containing per-zone counts per frame.

        Invariant: When availability != 'COUNTED', visible_count is strictly empty string.
        """
        output = io.StringIO()
        # Header comments with experimental disclaimer and provenance
        output.write(f"# CrowdSight Session Export: {session_info.get('id')}\n")
        output.write(f"# Checkpoint SHA-256: {session_info.get('checkpoint_sha256')}\n")
        output.write(f"# Synthetic: {session_info.get('synthetic', False)}\n")
        output.write(f"# DISCLAIMER: {EXPERIMENTAL_EXPORT_DISCLAIMER}\n")

        writer = csv.writer(output, lineterminator="\n")
        writer.writerow([
            "frame_index",
            "media_time_s",
            "zone_id",
            "zone_availability",
            "visible_count",
        ])

        # Sort chronologically, then by zone_id
        sorted_results = sorted(
            zone_results,
            key=lambda r: (float(r.get("media_time_s", 0.0)), str(r.get("zone_id", ""))),
        )

        for r in sorted_results:
            avail = str(r.get("availability", "UNKNOWN"))
            count_val = r.get("visible_count")
            # Invariant: Empty string if not COUNTED or count is None. Never 0!
            if avail == "COUNTED" and count_val is not None:
                count_str = str(count_val)
            else:
                count_str = ""

            writer.writerow([
                int(r.get("frame_index", 0)),
                f"{float(r.get('media_time_s', 0.0)):.3f}",
                str(r.get("zone_id", "")),
                avail,
                count_str,
            ])

        return output.getvalue()
