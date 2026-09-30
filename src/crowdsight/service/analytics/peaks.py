"""Highlight moments and peak visible person observations per zone."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PeakMoment:
    zone_id: str
    media_time_s: float
    frame_index: int
    visible_count: int
    description: str
    description_vi: str


def format_media_time(seconds: float) -> str:
    """Format seconds into MM:SS.SS format."""
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins:02d}:{secs:05.2f}"


class PeakAnalyzer:
    """Extracts top-k visible person observation moments using neutral language."""

    @staticmethod
    def find_peaks(
        zone_results: Sequence[dict[str, Any]],
        zone_id: str,
        limit: int = 5,
        min_separation_s: float = 2.0,
    ) -> list[PeakMoment]:
        """Find highest counted person moments for a zone.

        Applies temporal suppression to avoid reporting adjacent duplicate frames.
        Uses strictly descriptive, non-alarmist terminology.
        """
        # Filter for the target zone and counted availability
        valid_items = [
            r for r in zone_results
            if r.get("zone_id") == zone_id
            and r.get("availability") == "COUNTED"
            and r.get("visible_count") is not None
        ]

        if not valid_items:
            return []

        # Sort descending by visible_count, then ascending by media_time_s
        sorted_by_count = sorted(
            valid_items,
            key=lambda x: (int(x["visible_count"]), -float(x["media_time_s"])),
            reverse=True,
        )

        selected: list[dict[str, Any]] = []

        for item in sorted_by_count:
            if len(selected) >= limit:
                break
            t = float(item["media_time_s"])
            # Check separation with already selected
            is_separated = all(
                abs(t - float(s["media_time_s"])) >= min_separation_s
                for s in selected
            )
            if is_separated:
                selected.append(item)

        # Sort chronologically for final presentation
        selected.sort(key=lambda x: float(x["media_time_s"]))

        peaks: list[PeakMoment] = []
        for s in selected:
            t = float(s["media_time_s"])
            count = int(s["visible_count"])
            frame_idx = int(s.get("frame_index", 0))
            time_str = format_media_time(t)

            desc_en = (
                f"Peak visible count of {count} people observed at "
                f"{time_str} in zone '{zone_id}'."
            )
            desc_vi = (
                f"Thời điểm có số người nhìn thấy cao nhất: {count} người tại "
                f"{time_str} trong vùng '{zone_id}'."
            )

            peaks.append(
                PeakMoment(
                    zone_id=zone_id,
                    media_time_s=round(t, 3),
                    frame_index=frame_idx,
                    visible_count=count,
                    description=desc_en,
                    description_vi=desc_vi,
                )
            )

        return peaks
