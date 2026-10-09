/**
 * Congestion Alerts & Threshold Evaluation Utilities
 * Detects sustained crowd surges, evaluates zone safety thresholds,
 * and tracks real-time overcrowding violation intervals.
 */
import type { ZoneTrendLine } from '@/features/timeline/UnifiedTimeline';
import type { ZoneReading } from '@/shared/types/domain';

export type CongestionSeverity = 'WARNING' | 'CRITICAL';

export interface ZoneThresholdRule {
  zoneId: string;
  warningThreshold: number; // Level at which amber warning is triggered
  criticalThreshold: number; // Level at which red critical congestion alarm is triggered
  minDurationSeconds: number; // Minimum continuous violation to avoid transient blips (default: 1.0s)
}

export interface CongestionAlertEvent {
  id: string;
  zoneId: string;
  zoneName: string;
  zoneColor: string;
  severity: CongestionSeverity;
  startTime: number;
  endTime: number;
  peakCount: number;
  threshold: number;
  duration: number;
  exceedPercentage: number;
}

/**
 * Computes sensible default thresholds based on observed zone peaks.
 * If a zone peaked at 120 people:
 * - Warning: 65% of peak (~78 people)
 * - Critical: 85% of peak (~102 people)
 */
export function computeDefaultThresholds(
  zoneTrends: ZoneTrendLine[]
): Record<string, ZoneThresholdRule> {
  const rules: Record<string, ZoneThresholdRule> = {};

  for (const trend of zoneTrends) {
    let peak = 0;
    for (const pt of trend.points) {
      if (pt.count !== null && pt.count > peak) {
        peak = pt.count;
      }
    }

    if (peak <= 0) {
      rules[trend.zoneId] = {
        zoneId: trend.zoneId,
        warningThreshold: 20,
        criticalThreshold: 40,
        minDurationSeconds: 1.0,
      };
    } else {
      const warn = Math.max(5, Math.round(peak * 0.65));
      const crit = Math.max(warn + 3, Math.round(peak * 0.85));
      rules[trend.zoneId] = {
        zoneId: trend.zoneId,
        warningThreshold: warn,
        criticalThreshold: crit,
        minDurationSeconds: 1.0,
      };
    }
  }

  return rules;
}

/**
 * Detects sustained congestion periods across timeline trendlines for each zone.
 */
export function detectCongestionAlerts(
  zoneTrends: ZoneTrendLine[],
  thresholdRules: Record<string, ZoneThresholdRule>
): CongestionAlertEvent[] {
  const events: CongestionAlertEvent[] = [];

  for (const trend of zoneTrends) {
    const rule = thresholdRules[trend.zoneId];
    if (!rule) continue;

    const points = [...trend.points].sort((a, b) => a.time - b.time);
    if (points.length === 0) continue;

    let currentInterval: {
      severity: CongestionSeverity;
      startTime: number;
      endTime: number;
      peakCount: number;
      threshold: number;
    } | null = null;

    for (let i = 0; i < points.length; i++) {
      const pt = points[i]!;
      const count = pt.count;

      if (count === null) {
        // Unknown or missing frame ends the ongoing violation interval
        if (currentInterval) {
          const duration = currentInterval.endTime - currentInterval.startTime;
          if (duration >= rule.minDurationSeconds) {
            events.push({
              id: `alert-${trend.zoneId}-${currentInterval.startTime.toFixed(1)}`,
              zoneId: trend.zoneId,
              zoneName: trend.name,
              zoneColor: trend.color,
              severity: currentInterval.severity,
              startTime: Math.round(currentInterval.startTime * 10) / 10,
              endTime: Math.round(currentInterval.endTime * 10) / 10,
              peakCount: currentInterval.peakCount,
              threshold: currentInterval.threshold,
              duration: Math.round(duration * 10) / 10,
              exceedPercentage: Math.round(
                ((currentInterval.peakCount - currentInterval.threshold) / currentInterval.threshold) * 100
              ),
            });
          }
          currentInterval = null;
        }
        continue;
      }

      const isCritical = count >= rule.criticalThreshold;
      const isWarning = count >= rule.warningThreshold;

      if (isCritical) {
        if (!currentInterval) {
          currentInterval = {
            severity: 'CRITICAL',
            startTime: pt.time,
            endTime: pt.time,
            peakCount: count,
            threshold: rule.criticalThreshold,
          };
        } else {
          // Upgrade to critical if previously only warning
          if (currentInterval.severity === 'WARNING') {
            currentInterval.severity = 'CRITICAL';
            currentInterval.threshold = rule.criticalThreshold;
          }
          currentInterval.endTime = pt.time;
          if (count > currentInterval.peakCount) {
            currentInterval.peakCount = count;
          }
        }
      } else if (isWarning) {
        if (!currentInterval) {
          currentInterval = {
            severity: 'WARNING',
            startTime: pt.time,
            endTime: pt.time,
            peakCount: count,
            threshold: rule.warningThreshold,
          };
        } else {
          currentInterval.endTime = pt.time;
          if (count > currentInterval.peakCount) {
            currentInterval.peakCount = count;
          }
        }
      } else {
        // Below threshold - close current interval if exists
        if (currentInterval) {
          const duration = currentInterval.endTime - currentInterval.startTime;
          if (duration >= rule.minDurationSeconds) {
            events.push({
              id: `alert-${trend.zoneId}-${currentInterval.startTime.toFixed(1)}`,
              zoneId: trend.zoneId,
              zoneName: trend.name,
              zoneColor: trend.color,
              severity: currentInterval.severity,
              startTime: Math.round(currentInterval.startTime * 10) / 10,
              endTime: Math.round(currentInterval.endTime * 10) / 10,
              peakCount: currentInterval.peakCount,
              threshold: currentInterval.threshold,
              duration: Math.round(duration * 10) / 10,
              exceedPercentage: Math.round(
                ((currentInterval.peakCount - currentInterval.threshold) / currentInterval.threshold) * 100
              ),
            });
          }
          currentInterval = null;
        }
      }
    }

    // Flush trailing interval
    if (currentInterval) {
      const duration = currentInterval.endTime - currentInterval.startTime;
      if (duration >= rule.minDurationSeconds) {
        events.push({
          id: `alert-${trend.zoneId}-${currentInterval.startTime.toFixed(1)}`,
          zoneId: trend.zoneId,
          zoneName: trend.name,
          zoneColor: trend.color,
          severity: currentInterval.severity,
          startTime: Math.round(currentInterval.startTime * 10) / 10,
          endTime: Math.round(currentInterval.endTime * 10) / 10,
          peakCount: currentInterval.peakCount,
          threshold: currentInterval.threshold,
          duration: Math.round(duration * 10) / 10,
          exceedPercentage: Math.round(
            ((currentInterval.peakCount - currentInterval.threshold) / currentInterval.threshold) * 100
          ),
        });
      }
    }
  }

  // Sort chronologically by startTime
  return events.sort((a, b) => a.startTime - b.startTime);
}

/**
 * Checks for live alerts on the current frame based on active readings.
 */
export function checkActiveCongestionAlerts(
  currentTime: number,
  readings: ZoneReading[],
  thresholdRules: Record<string, ZoneThresholdRule>,
  zones: { zone_id: string; name: string; color: string }[]
): CongestionAlertEvent[] {
  const activeAlerts: CongestionAlertEvent[] = [];
  const zoneMap = new Map(zones.map((z) => [z.zone_id, z]));

  for (const r of readings) {
    if (r.status !== 'COUNTED') continue;
    const rule = thresholdRules[r.zoneId];
    if (!rule) continue;

    const zInfo = zoneMap.get(r.zoneId);
    const zoneName = r.zoneName || zInfo?.name || r.zoneId;
    const zoneColor = zInfo?.color || '#0072B2';

    if (r.count >= rule.criticalThreshold) {
      activeAlerts.push({
        id: `active-crit-${r.zoneId}-${currentTime.toFixed(1)}`,
        zoneId: r.zoneId,
        zoneName,
        zoneColor,
        severity: 'CRITICAL',
        startTime: currentTime,
        endTime: currentTime,
        peakCount: r.count,
        threshold: rule.criticalThreshold,
        duration: 0,
        exceedPercentage: Math.round(((r.count - rule.criticalThreshold) / rule.criticalThreshold) * 100),
      });
    } else if (r.count >= rule.warningThreshold) {
      activeAlerts.push({
        id: `active-warn-${r.zoneId}-${currentTime.toFixed(1)}`,
        zoneId: r.zoneId,
        zoneName,
        zoneColor,
        severity: 'WARNING',
        startTime: currentTime,
        endTime: currentTime,
        peakCount: r.count,
        threshold: rule.warningThreshold,
        duration: 0,
        exceedPercentage: Math.round(((r.count - rule.warningThreshold) / rule.warningThreshold) * 100),
      });
    }
  }

  return activeAlerts;
}
