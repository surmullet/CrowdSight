"""Session quality summary, reason code distributions, and raw score histograms."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ZoneAvailabilitySummary:
    zone_id: str
    n_frames: int
    n_counted: int
    availability_ratio: float


@dataclass(frozen=True, slots=True)
class ScoreBin:
    bin_range: str
    lower: float
    upper: float
    count: int
    ratio: float


@dataclass(frozen=True, slots=True)
class QualitySummary:
    session_id: str
    total_frames: int
    duration_s: float
    processing_fps: float
    valid_frames: int
    partial_frames: int
    unknown_frames: int
    stale_frames: int
    valid_ratio: float
    partial_ratio: float
    unknown_ratio: float
    stale_ratio: float
    zone_availability: dict[str, ZoneAvailabilitySummary]
    reason_code_distribution: dict[str, int]
    raw_score_distribution: list[ScoreBin]
    synthetic: bool
    completeness: str
    applicability_status: str
    operational_alerts_allowed: bool
    experimental_warning: str


class QualitySummaryCalculator:
    """Calculates truthful quality metrics and confidence score distributions."""

    @staticmethod
    def calculate(
        session_id: str,
        observations: Sequence[dict[str, Any]],
        zone_results: Sequence[dict[str, Any]],
        zone_ids: Sequence[str],
        duration_s: float,
        processing_time_s: float = 0.0,
        synthetic: bool = False,
        completeness: str = "COMPLETE",
        applicability_snapshot: dict[str, Any] | None = None,
    ) -> QualitySummary:
        total_obs = len(observations)
        valid_cnt = 0
        partial_cnt = 0
        unknown_cnt = 0
        stale_cnt = 0
        reason_dist: dict[str, int] = {}
        all_raw_scores: list[float] = []

        for obs in observations:
            q = str(obs.get("quality", "UNKNOWN"))
            if q == "VALID":
                valid_cnt += 1
            elif q == "PARTIAL":
                partial_cnt += 1
            elif q == "STALE":
                stale_cnt += 1
            else:
                unknown_cnt += 1

            rc = obs.get("reason_code")
            if rc:
                reason_dist[str(rc)] = reason_dist.get(str(rc), 0) + 1

            for det in obs.get("detections", []):
                score = float(det.get("confidence", 0.0))
                all_raw_scores.append(score)

        fps = (total_obs / processing_time_s) if processing_time_s > 0.0 else 0.0

        # Zone availability calculation
        zone_avail_map: dict[str, ZoneAvailabilitySummary] = {}
        for zid in zone_ids:
            matching = [r for r in zone_results if r.get("zone_id") == zid]
            n_frames_zone = len(matching)
            n_counted = sum(
                1 for r in matching
                if r.get("availability") == "COUNTED" and r.get("visible_count") is not None
            )
            ratio = (n_counted / n_frames_zone) if n_frames_zone > 0 else 0.0
            zone_avail_map[zid] = ZoneAvailabilitySummary(
                zone_id=zid,
                n_frames=n_frames_zone,
                n_counted=n_counted,
                availability_ratio=round(ratio, 4),
            )

        # 10-bin histogram of raw model scores
        bins: list[ScoreBin] = []
        num_scores = len(all_raw_scores)
        for i in range(10):
            lower = round(i * 0.1, 1)
            upper = round((i + 1) * 0.1, 1)
            if i == 9:
                count = sum(1 for s in all_raw_scores if lower <= s <= 1.0)
            else:
                count = sum(1 for s in all_raw_scores if lower <= s < upper)
            ratio = (count / num_scores) if num_scores > 0 else 0.0
            bins.append(
                ScoreBin(
                    bin_range=f"{lower:.1f}-{upper:.1f}",
                    lower=lower,
                    upper=upper,
                    count=count,
                    ratio=round(ratio, 4),
                )
            )

        app_snap = applicability_snapshot or {}
        app_status = str(app_snap.get("status", "EXPERIMENTAL_NO_APPROVAL"))
        alerts_allowed = bool(app_snap.get("operational_alerts_allowed", False))

        return QualitySummary(
            session_id=session_id,
            total_frames=total_obs,
            duration_s=round(duration_s, 3),
            processing_fps=round(fps, 1),
            valid_frames=valid_cnt,
            partial_frames=partial_cnt,
            unknown_frames=unknown_cnt,
            stale_frames=stale_cnt,
            valid_ratio=round(valid_cnt / total_obs, 4) if total_obs > 0 else 0.0,
            partial_ratio=round(partial_cnt / total_obs, 4) if total_obs > 0 else 0.0,
            unknown_ratio=round(unknown_cnt / total_obs, 4) if total_obs > 0 else 0.0,
            stale_ratio=round(stale_cnt / total_obs, 4) if total_obs > 0 else 0.0,
            zone_availability=zone_avail_map,
            reason_code_distribution=reason_dist,
            raw_score_distribution=bins,
            synthetic=synthetic,
            completeness=completeness,
            applicability_status=app_status,
            operational_alerts_allowed=alerts_allowed,
            experimental_warning="Thử nghiệm — mô hình chưa được duyệt cho vận hành thực tế. Có thể đếm thiếu ở cảnh đông.",
        )
