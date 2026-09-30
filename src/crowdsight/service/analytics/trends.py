"""Time trend analytics with bucketing, robust statistics, smoothing, and LTTB downsampling."""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np


class SeriesMode(str, Enum):
    RAW = "RAW"
    BUCKETED = "BUCKETED"
    SMOOTHED = "SMOOTHED"


@dataclass(frozen=True, slots=True)
class TrendPoint:
    media_time_s: float
    visible_count: int | None
    availability: str


@dataclass(frozen=True, slots=True)
class TrendBucket:
    bucket_index: int
    from_t: float
    to_t: float
    n_frames: int
    n_counted: int
    availability_ratio: float
    min: float | None
    mean: float | None
    median: float | None
    p95: float | None
    max: float | None


@dataclass(frozen=True, slots=True)
class SmoothedPoint:
    media_time_s: float
    smoothed_value: float | None
    is_derived: bool = True


def lttb_downsample(
    points: Sequence[tuple[float, float | None]],
    threshold: int,
) -> list[tuple[float, float | None]]:
    """Downsample (x, y) points using Largest-Triangle-Three-Buckets (LTTB).

    Preserves None values (missing intervals) without coercing them to zero.
    """
    n = len(points)
    if threshold >= n or threshold <= 2:
        return list(points)

    # First point is always selected
    sampled: list[tuple[float, float | None]] = [points[0]]

    # Bucket size for the intermediate points
    every = (n - 2) / (threshold - 2)
    a = 0

    for i in range(threshold - 2):
        # Calculate point average for next bucket (bucket c)
        avg_x = 0.0
        avg_y = 0.0
        avg_count = 0

        c_start = int(math.floor((i + 1) * every)) + 1
        c_end = int(math.floor((i + 2) * every)) + 1
        c_end = min(c_end, n)

        for idx in range(c_start, c_end):
            pt_x, pt_y = points[idx]
            avg_x += pt_x
            if pt_y is not None:
                avg_y += pt_y
                avg_count += 1

        if (c_end - c_start) > 0:
            avg_x /= (c_end - c_start)
        if avg_count > 0:
            avg_y /= avg_count
        else:
            avg_y = 0.0

        # Get range for current bucket (bucket b)
        b_start = int(math.floor(i * every)) + 1
        b_end = int(math.floor((i + 1) * every)) + 1
        b_end = min(b_end, n)

        # Point a coordinates
        point_a_x, point_a_y = points[a]
        ref_a_y = point_a_y if point_a_y is not None else avg_y

        max_area = -1.0
        next_a = b_start

        for idx in range(b_start, b_end):
            pt_x, pt_y = points[idx]
            ref_b_y = pt_y if pt_y is not None else avg_y

            # Triangle area: 0.5 * abs((xA - xC)*(yB - yA) - (xA - xB)*(yC - yA))
            area = abs(
                (point_a_x - avg_x) * (ref_b_y - ref_a_y)
                - (point_a_x - pt_x) * (avg_y - ref_a_y)
            ) * 0.5

            if area > max_area:
                max_area = area
                next_a = idx

        sampled.append(points[next_a])
        a = next_a

    # Last point is always selected
    sampled.append(points[-1])
    return sampled


class TrendAnalyzer:
    """Computes trends, bucket aggregates, and derived smoothed series."""

    @staticmethod
    def compute_buckets(
        records: Sequence[dict[str, Any]],
        bucket_s: float = 1.0,
        total_duration_s: float | None = None,
    ) -> list[TrendBucket]:
        """Group chronological frame records into time buckets.

        Each record must contain 'media_time_s', 'availability', and 'visible_count'.
        """
        if not records:
            return []

        sorted_records = sorted(records, key=lambda r: float(r["media_time_s"]))
        min_t = 0.0
        max_t = total_duration_s if total_duration_s is not None else float(sorted_records[-1]["media_time_s"])
        if max_t < min_t:
            max_t = float(sorted_records[-1]["media_time_s"])

        if bucket_s <= 0.0:
            bucket_s = 1.0

        num_buckets = max(1, int(math.ceil((max_t - min_t) / bucket_s)))
        # Handle single frame at 0.0
        if num_buckets == 0:
            num_buckets = 1

        buckets_data: list[list[dict[str, Any]]] = [[] for _ in range(num_buckets)]

        for r in sorted_records:
            t = float(r["media_time_s"])
            b_idx = int((t - min_t) // bucket_s)
            b_idx = min(max(0, b_idx), num_buckets - 1)
            buckets_data[b_idx].append(r)

        result: list[TrendBucket] = []
        for i, b_records in enumerate(buckets_data):
            from_t = min_t + i * bucket_s
            to_t = from_t + bucket_s
            n_frames = len(b_records)
            counted_vals = [
                int(r["visible_count"])
                for r in b_records
                if r.get("availability") == "COUNTED" and r.get("visible_count") is not None
            ]
            n_counted = len(counted_vals)
            avail_ratio = (n_counted / n_frames) if n_frames > 0 else 0.0

            if n_counted == 0:
                # Strictly null when no counted frames exist! Never 0!
                b_min: float | None = None
                b_mean: float | None = None
                b_median: float | None = None
                b_p95: float | None = None
                b_max: float | None = None
            else:
                arr = np.array(counted_vals, dtype=np.float64)
                b_min = float(np.min(arr))
                b_mean = float(np.mean(arr))
                b_median = float(np.median(arr))
                b_p95 = float(np.percentile(arr, 95))
                b_max = float(np.max(arr))

            result.append(
                TrendBucket(
                    bucket_index=i,
                    from_t=round(from_t, 3),
                    to_t=round(to_t, 3),
                    n_frames=n_frames,
                    n_counted=n_counted,
                    availability_ratio=round(avail_ratio, 4),
                    min=b_min,
                    mean=round(b_mean, 2) if b_mean is not None else None,
                    median=round(b_median, 2) if b_median is not None else None,
                    p95=round(b_p95, 2) if b_p95 is not None else None,
                    max=b_max,
                )
            )

        return result

    @staticmethod
    def compute_smoothed(
        raw_points: Sequence[TrendPoint],
        window_size: int = 5,
    ) -> list[SmoothedPoint]:
        """Compute rolling average over counted values.

        Uncounted intervals remain None (gaps).
        """
        if not raw_points:
            return []

        result: list[SmoothedPoint] = []
        half_w = window_size // 2

        for i, pt in enumerate(raw_points):
            if pt.availability != "COUNTED" or pt.visible_count is None:
                result.append(SmoothedPoint(media_time_s=pt.media_time_s, smoothed_value=None))
                continue

            # Gather window neighbors that are counted
            w_start = max(0, i - half_w)
            w_end = min(len(raw_points), i + half_w + 1)
            valid_vals = [
                p.visible_count
                for p in raw_points[w_start:w_end]
                if p.availability == "COUNTED" and p.visible_count is not None
            ]

            if not valid_vals:
                result.append(SmoothedPoint(media_time_s=pt.media_time_s, smoothed_value=None))
            else:
                avg = float(np.mean(valid_vals))
                result.append(SmoothedPoint(media_time_s=pt.media_time_s, smoothed_value=round(avg, 2)))

        return result
