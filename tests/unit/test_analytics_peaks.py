"""Unit tests for peak moment analytics and neutral language verification."""
from __future__ import annotations

from crowdsight.service.analytics.peaks import PeakAnalyzer

FORBIDDEN_WORDS = [
    "cảnh báo",
    "nguy hiểm",
    "sức chứa",
    "quá tải",
    "vượt ngưỡng",
    "attendance",
    "capacity",
    "danger",
    "alert",
]


def test_peak_analyzer_returns_empty_on_no_counted() -> None:
    records = [
        {"zone_id": "zone_a", "media_time_s": 1.0, "availability": "UNKNOWN", "visible_count": None},
    ]
    peaks = PeakAnalyzer.find_peaks(records, zone_id="zone_a", limit=5)
    assert peaks == []


def test_peak_analyzer_finds_highest_counts_with_neutral_descriptions() -> None:
    records = [
        {"zone_id": "zone_a", "media_time_s": 1.0, "frame_index": 10, "availability": "COUNTED", "visible_count": 5},
        {"zone_id": "zone_a", "media_time_s": 1.1, "frame_index": 11, "availability": "COUNTED", "visible_count": 6},
        {"zone_id": "zone_a", "media_time_s": 5.0, "frame_index": 50, "availability": "COUNTED", "visible_count": 15},
        {"zone_id": "zone_a", "media_time_s": 10.0, "frame_index": 100, "availability": "COUNTED", "visible_count": 22},
    ]

    peaks = PeakAnalyzer.find_peaks(records, zone_id="zone_a", limit=2, min_separation_s=2.0)
    assert len(peaks) == 2
    # Chronologically sorted for final presentation
    assert peaks[0].visible_count == 15
    assert peaks[0].media_time_s == 5.0
    assert peaks[1].visible_count == 22
    assert peaks[1].media_time_s == 10.0

    # Verify no alarmist or capacity terminology
    for p in peaks:
        for fw in FORBIDDEN_WORDS:
            assert fw.lower() not in p.description.lower()
            assert fw.lower() not in p.description_vi.lower()
