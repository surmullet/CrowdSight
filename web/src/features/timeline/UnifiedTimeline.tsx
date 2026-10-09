import React, { useRef, useState, useCallback, useMemo } from 'react';
import type { FrameQuality } from '@/shared/types/domain';
import { formatMediaTime } from '@/features/player/PlayerControls';

export interface QualityInterval {
  startTime: number;
  endTime: number;
  quality: FrameQuality;
  reasonCode?: string;
  frameCount?: number;
}

export interface TimelineDataPoint {
  time: number;
  count: number | null; // null represents missing/unknown/stale — strictly gap!
}

export interface ZoneTrendLine {
  zoneId: string;
  name: string;
  color: string;
  points: TimelineDataPoint[];
}

export interface PeakMarker {
  time: number;
  count: number;
  zoneId: string;
  label?: string;
}

export interface NoteMarker {
  id: string;
  time: number;
  text: string;
  zoneId?: string;
}

import type { ZoneThresholdRule, CongestionAlertEvent } from '@/features/alerts/alertUtils';

interface UnifiedTimelineProps {
  duration: number;
  currentTime: number;
  qualityIntervals: QualityInterval[];
  zoneTrends: ZoneTrendLine[];
  peaks?: PeakMarker[];
  notes?: NoteMarker[];
  thresholdRules?: Record<string, ZoneThresholdRule>;
  alerts?: CongestionAlertEvent[];
  missingFramesCount?: number;
  onSeek: (time: number) => void;
  className?: string;
}

export const UnifiedTimeline: React.FC<UnifiedTimelineProps> = ({
  duration,
  currentTime,
  qualityIntervals,
  zoneTrends,
  peaks = [],
  notes = [],
  thresholdRules = {},
  alerts = [],
  missingFramesCount = 0,
  onSeek,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [hoverTime, setHoverTime] = useState<number | null>(null);

  const safeDuration = Math.max(0.1, duration);

  // Compute maximum count across all trends to scale Y axis
  const maxCount = useMemo(() => {
    let max = 1;
    for (const trend of zoneTrends) {
      for (const pt of trend.points) {
        if (pt.count !== null && pt.count > max) {
          max = pt.count;
        }
      }
    }
    return Math.ceil(max * 1.15); // Add 15% headroom
  }, [zoneTrends]);

  // Convert client coordinate to timeline seconds
  const getTimeFromEvent = useCallback(
    (e: React.MouseEvent | MouseEvent): number => {
      const container = containerRef.current;
      if (!container) return 0;
      const rect = container.getBoundingClientRect();
      const clientX = 'clientX' in e ? e.clientX : 0;
      const fraction = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
      return fraction * safeDuration;
    },
    [safeDuration]
  );

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    const newTime = getTimeFromEvent(e);
    onSeek(newTime);

    const onMouseMove = (moveEvent: MouseEvent) => {
      onSeek(getTimeFromEvent(moveEvent));
    };

    const onMouseUp = () => {
      setIsDragging(false);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    setHoverTime(getTimeFromEvent(e));
  };

  const handleMouseLeave = () => {
    setHoverTime(null);
  };

  // Keyboard navigation for accessibility
  const handleKeyDown = (e: React.KeyboardEvent) => {
    let delta = 0;
    if (e.key === 'ArrowLeft') delta = e.shiftKey ? -1.0 : -0.1;
    if (e.key === 'ArrowRight') delta = e.shiftKey ? 1.0 : 0.1;
    if (e.key === 'Home') {
      e.preventDefault();
      onSeek(0);
      return;
    }
    if (e.key === 'End') {
      e.preventDefault();
      onSeek(safeDuration);
      return;
    }
    if (delta !== 0) {
      e.preventDefault();
      onSeek(Math.max(0, Math.min(safeDuration, currentTime + delta)));
    }
  };

  // Build SVG path segments with physical gaps for null points
  const generatePathSegments = (points: TimelineDataPoint[], width: number, height: number): string => {
    const sorted = [...points].sort((a, b) => a.time - b.time);
    let path = '';
    let inSubpath = false;

    for (const pt of sorted) {
      if (pt.count === null) {
        // Gap encountered — break line!
        inSubpath = false;
        continue;
      }

      const x = (pt.time / safeDuration) * width;
      const y = height - (pt.count / maxCount) * height;

      if (!inSubpath) {
        path += ` M ${x.toFixed(1)} ${y.toFixed(1)}`;
        inSubpath = true;
      } else {
        path += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
      }
    }
    return path;
  };

  const progressPercent = Math.min(100, Math.max(0, (currentTime / safeDuration) * 100));

  return (
    <div className={`space-y-1 select-none ${className}`}>
      {/* Top status info line: missing frames count indicator */}
      <div className="flex items-center justify-between text-[11px] text-brand-text-muted px-1">
        <div className="flex items-center gap-3">
          <span className="font-mono text-brand-gold font-medium tabular-nums">
            {formatMediaTime(currentTime)}
          </span>
          {missingFramesCount > 0 && (
            <span className="text-amber-400/90 text-[10px]">
              ⚠️ {missingFramesCount} khung không có số liệu (khoảng trống)
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 text-[10px]">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500/60 inline-block" /> VALID
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-500/60 inline-block" /> PARTIAL
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-slate-500/60 inline-block" /> UNKNOWN
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500/60 inline-block" /> STALE
          </span>
        </div>
      </div>

      {/* Main interactive scrubber container */}
      <div
        ref={containerRef}
        role="slider"
        tabIndex={0}
        aria-label="Thanh dòng thời gian và chất lượng quan sát"
        aria-valuemin={0}
        aria-valuemax={safeDuration}
        aria-valuenow={currentTime}
        aria-valuetext={formatMediaTime(currentTime)}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        onKeyDown={handleKeyDown}
        className="relative w-full h-24 bg-brand-abyssal rounded-lg border border-brand-border overflow-hidden cursor-crosshair focus-visible:ring-2 focus-visible:ring-brand-gold outline-none"
      >
        {/* Tier 1: Quality Ribbon (Top 12px) */}
        <div className="absolute top-0 left-0 right-0 h-3 flex bg-brand-surface border-b border-brand-border/40">
          {qualityIntervals.map((interval, idx) => {
            const startPct = (interval.startTime / safeDuration) * 100;
            const endPct = (interval.endTime / safeDuration) * 100;
            const widthPct = Math.max(0.2, endPct - startPct);

            let bgStyle = 'bg-brand-surface';
            if (interval.quality === 'VALID') bgStyle = 'bg-emerald-950/40 border-r border-emerald-900/30';
            if (interval.quality === 'PARTIAL') bgStyle = 'pattern-diagonal-hatching bg-amber-950/30 border-r border-amber-900/30';
            if (interval.quality === 'UNKNOWN') bgStyle = 'pattern-dot-stipple bg-slate-900/60 border-r border-slate-800';
            if (interval.quality === 'STALE') bgStyle = 'bg-red-950/30 border-r border-red-900/30';

            return (
              <div
                key={`q-${idx}`}
                style={{ left: `${startPct}%`, width: `${widthPct}%` }}
                className={`absolute top-0 bottom-0 ${bgStyle}`}
                title={`[${formatMediaTime(interval.startTime)} - ${formatMediaTime(interval.endTime)}] ${interval.quality}${
                  interval.reasonCode ? `: ${interval.reasonCode}` : ''
                }`}
              />
            );
          })}
        </div>

        {/* Tier 2: Trend Lines (Sparkline SVG, Middle 64px) */}
        <div className="absolute top-3 left-0 right-0 h-16 pointer-events-none">
          <svg className="w-full h-full" viewBox="0 0 1000 64" preserveAspectRatio="none">
            {/* Grid line at 50% max */}
            <line x1="0" y1="32" x2="1000" y2="32" stroke="#222D3E" strokeDasharray="3,3" strokeWidth="0.5" />

            {/* Threshold Warning & Critical Lines */}
            {Object.values(thresholdRules).map((rule) => {
              const critY = Math.max(0, Math.min(64, 64 - (rule.criticalThreshold / maxCount) * 64));
              const warnY = Math.max(0, Math.min(64, 64 - (rule.warningThreshold / maxCount) * 64));
              return (
                <React.Fragment key={`thresh-${rule.zoneId}`}>
                  {rule.criticalThreshold <= maxCount && (
                    <line
                      x1="0"
                      y1={critY}
                      x2="1000"
                      y2={critY}
                      stroke="#EF4444"
                      strokeDasharray="4,4"
                      strokeWidth="0.8"
                      strokeOpacity="0.75"
                    />
                  )}
                  {rule.warningThreshold <= maxCount && (
                    <line
                      x1="0"
                      y1={warnY}
                      x2="1000"
                      y2={warnY}
                      stroke="#F59E0B"
                      strokeDasharray="3,3"
                      strokeWidth="0.6"
                      strokeOpacity="0.65"
                    />
                  )}
                </React.Fragment>
              );
            })}

            {/* Render each zone trend line */}
            {zoneTrends.map((trend) => {
              const pathData = generatePathSegments(trend.points, 1000, 64);
              if (!pathData) return null;

              return (
                <path
                  key={trend.zoneId}
                  d={pathData}
                  fill="none"
                  stroke={trend.color}
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              );
            })}
          </svg>
        </div>

        {/* Congestion Alert Highlight Bands on Timeline Track */}
        {alerts.map((alert) => {
          const startPct = (alert.startTime / safeDuration) * 100;
          const endPct = (alert.endTime / safeDuration) * 100;
          const widthPct = Math.max(0.4, endPct - startPct);
          return (
            <div
              key={`alert-band-${alert.id}`}
              style={{ left: `${startPct}%`, width: `${widthPct}%` }}
              className={`absolute top-0 bottom-0 pointer-events-auto cursor-pointer transition-opacity ${
                alert.severity === 'CRITICAL'
                  ? 'bg-red-500/20 border-x border-red-500/60 hover:bg-red-500/30'
                  : 'bg-amber-500/15 border-x border-amber-500/50 hover:bg-amber-500/25'
              }`}
              onClick={(e) => {
                e.stopPropagation();
                onSeek(alert.startTime);
              }}
              title={`🚨 [Quá tải ${alert.severity === 'CRITICAL' ? 'Nguy hiểm' : 'Cảnh báo'}] ${alert.zoneName}: ${alert.peakCount} người tại ${formatMediaTime(alert.startTime)} - ${formatMediaTime(alert.endTime)}`}
            />
          );
        })}

        {/* Tier 3: Peak and Note Markers (Bottom 18px) */}
        <div className="absolute bottom-0 left-0 right-0 h-4 bg-brand-surface/40 border-t border-brand-border/40 pointer-events-none">
          {/* Peaks */}
          {peaks.map((peak, idx) => {
            const leftPct = (peak.time / safeDuration) * 100;
            return (
              <div
                key={`peak-${idx}`}
                style={{ left: `${leftPct}%` }}
                className="absolute -top-1.5 -ml-1.5 w-3 h-3 flex items-center justify-center"
                title={`Khoảnh khắc cao điểm: ${peak.count} người tại ${formatMediaTime(peak.time)} (${peak.label || ''})`}
              >
                <div className="w-2 h-2 bg-brand-gold rotate-45 border border-white/60" />
              </div>
            );
          })}

          {/* Notes */}
          {notes.map((note) => {
            const leftPct = (note.time / safeDuration) * 100;
            return (
              <div
                key={`note-${note.id}`}
                style={{ left: `${leftPct}%` }}
                className="absolute top-0.5 -ml-1 w-2 h-2 rounded-full bg-cyan-400 ring-1 ring-cyan-200"
                title={`Ghi chú [${formatMediaTime(note.time)}]: ${note.text}`}
              />
            );
          })}

          {/* Alert Flag Markers */}
          {alerts.map((alert) => {
            const leftPct = (alert.startTime / safeDuration) * 100;
            return (
              <div
                key={`alert-flag-${alert.id}`}
                style={{ left: `${leftPct}%` }}
                onClick={(e) => {
                  e.stopPropagation();
                  onSeek(alert.startTime);
                }}
                className="absolute -top-2 -ml-2 w-4 h-4 flex items-center justify-center cursor-pointer pointer-events-auto"
                title={`🚨 [Quá tải ${alert.severity === 'CRITICAL' ? 'Nguy hiểm' : 'Cảnh báo'}] ${alert.zoneName}: ${alert.peakCount} người tại ${formatMediaTime(alert.startTime)}`}
              >
                <span className="text-[10px] leading-none select-none">
                  {alert.severity === 'CRITICAL' ? '🚨' : '⚠️'}
                </span>
              </div>
            );
          })}
        </div>

        {/* Hover preview needle */}
        {hoverTime !== null && !isDragging && (
          <div
            style={{ left: `${(hoverTime / safeDuration) * 100}%` }}
            className="absolute top-0 bottom-0 w-px bg-white/40 pointer-events-none"
          >
            <div className="absolute top-1 -translate-x-1/2 px-1 py-0.5 bg-brand-abyssal/90 border border-brand-border rounded text-[9px] font-mono text-brand-text-primary whitespace-nowrap">
              {formatMediaTime(hoverTime)}
            </div>
          </div>
        )}

        {/* Current Time Needle / Scrubber Handle */}
        <div
          style={{ left: `${progressPercent}%` }}
          className="absolute top-0 bottom-0 w-0.5 bg-brand-gold pointer-events-none z-10"
        >
          {/* Thumb marker */}
          <div className="absolute -top-0.5 -translate-x-1/2 w-2.5 h-3 bg-brand-gold rounded-b-sm shadow-md" />
        </div>
      </div>

      {/* Screen reader accessible table representation */}
      <div className="sr-only">
        <h4>Dữ liệu chất lượng và người nhìn thấy theo thời gian</h4>
        <table>
          <thead>
            <tr>
              <th>Khoảng thời gian</th>
              <th>Chất lượng</th>
              <th>Lý do</th>
            </tr>
          </thead>
          <tbody>
            {qualityIntervals.map((int, i) => (
              <tr key={i}>
                <td>{`${formatMediaTime(int.startTime)} - ${formatMediaTime(int.endTime)}`}</td>
                <td>{int.quality}</td>
                <td>{int.reasonCode || 'N/A'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
