"""Unit tests for trend analytics, bucketing, missing data handling, and LTTB downsampling."""
from __future__ import annotations

from crowdsight.service.analytics.trends import (
    TrendAnalyzer,
    TrendPoint,
    lttb_downsample,
)


def test_empty_records_returns_empty_buckets() -> None:
    assert TrendAnalyzer.compute_buckets([], bucket_s=1.0) == []


def test_bucket_with_zero_counted_frames_is_strictly_none() -> None:
    """Invariant: When a bucket has 0 counted frames, summary statistics MUST be None, NEVER 0.0."""
    records = [
        {"media_time_s": 0.1, "availability": "UNKNOWN", "visible_count": None},
        {"media_time_s": 0.5, "availability": "NOT_FULLY_OBSERVED", "visible_count": None},
        {"media_time_s": 0.9, "availability": "STALE", "visible_count": None},
    ]

    buckets = TrendAnalyzer.compute_buckets(records, bucket_s=1.0, total_duration_s=1.0)
    assert len(buckets) == 1
    b = buckets[0]

    assert b.n_frames == 3
    assert b.n_counted == 0
    assert b.availability_ratio == 0.0
    assert b.min is None
    assert b.mean is None
    assert b.median is None
    assert b.p95 is None
    assert b.max is None


def test_bucket_with_counted_frames_computes_exact_statistics() -> None:
    records = [
        {"media_time_s": 0.1, "availability": "COUNTED", "visible_count": 10},
        {"media_time_s": 0.3, "availability": "COUNTED", "visible_count": 20},
        {"media_time_s": 0.5, "availability": "UNKNOWN", "visible_count": None},
        {"media_time_s": 0.8, "availability": "COUNTED", "visible_count": 30},
    ]

    buckets = TrendAnalyzer.compute_buckets(records, bucket_s=1.0, total_duration_s=1.0)
    assert len(buckets) == 1
    b = buckets[0]

    assert b.n_frames == 4
    assert b.n_counted == 3
    assert b.availability_ratio == 0.75
    assert b.min == 10.0
    assert b.mean == 20.0
    assert b.median == 20.0
    assert b.max == 30.0


def test_smoothed_series_preserves_uncounted_gaps() -> None:
    pts = [
        TrendPoint(media_time_s=0.0, visible_count=10, availability="COUNTED"),
        TrendPoint(media_time_s=1.0, visible_count=12, availability="COUNTED"),
        TrendPoint(media_time_s=2.0, visible_count=None, availability="UNKNOWN"),
        TrendPoint(media_time_s=3.0, visible_count=14, availability="COUNTED"),
    ]

    smoothed = TrendAnalyzer.compute_smoothed(pts, window_size=3)
    assert len(smoothed) == 4
    assert smoothed[0].smoothed_value is not None
    assert smoothed[1].smoothed_value is not None
    # Index 2 was UNKNOWN -> must remain None (gap)
    assert smoothed[2].smoothed_value is None
    assert smoothed[3].smoothed_value is not None


def test_lttb_downsampling_handles_none_values() -> None:
    raw: list[tuple[float, float | None]] = [
        (0.0, 10.0),
        (1.0, 15.0),
        (2.0, None),
        (3.0, 20.0),
        (4.0, 50.0),  # Peak
        (5.0, 10.0),
        (6.0, 5.0),
    ]

    sampled = lttb_downsample(raw, threshold=4)
    assert len(sampled) == 4
    assert sampled[0] == raw[0]
    assert sampled[-1] == raw[-1]
    # Check that points retain correct structure
    for t, val in sampled:
        assert isinstance(t, float)
        assert val is None or isinstance(val, float)
