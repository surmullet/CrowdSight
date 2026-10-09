import { describe, it, expect } from 'vitest';
import {
  computeDefaultThresholds,
  detectCongestionAlerts,
  checkActiveCongestionAlerts,
  type ZoneThresholdRule,
} from './alertUtils';
import type { ZoneTrendLine } from '@/features/timeline/UnifiedTimeline';
import type { ZoneReading } from '@/shared/types/domain';

const mockTrends: ZoneTrendLine[] = [
  {
    zoneId: 'zone-plaza',
    name: 'Quảng Trường',
    color: '#0072B2',
    points: [
      { time: 0, count: 20 },
      { time: 2, count: 55 },
      { time: 4, count: 85 }, // Critical spike
      { time: 6, count: 90 }, // Critical
      { time: 8, count: 52 }, // Warning
      { time: 10, count: 15 }, // Normal
    ],
  },
  {
    zoneId: 'zone-gate',
    name: 'Cổng Vào',
    color: '#009E73',
    points: [
      { time: 0, count: 5 },
      { time: 5, count: 10 },
      { time: 10, count: 8 },
    ],
  },
];

describe('alertUtils', () => {
  it('computes reasonable default warning and critical thresholds from trend peak', () => {
    const rules = computeDefaultThresholds(mockTrends);

    expect(rules['zone-plaza']).toBeDefined();
    // Peak for plaza is 90 -> warn 65% ~ 59, crit 85% ~ 77
    expect(rules['zone-plaza']!.warningThreshold).toBe(59);
    expect(rules['zone-plaza']!.criticalThreshold).toBe(77);
    expect(rules['zone-plaza']!.minDurationSeconds).toBe(1.0);

    // Peak for gate is 10 -> warn 7, crit 10
    expect(rules['zone-gate']!.warningThreshold).toBe(7);
    expect(rules['zone-gate']!.criticalThreshold).toBe(10);
  });

  it('detects sustained congestion alert events exceeding threshold', () => {
    const rules: Record<string, ZoneThresholdRule> = {
      'zone-plaza': {
        zoneId: 'zone-plaza',
        warningThreshold: 50,
        criticalThreshold: 80,
        minDurationSeconds: 1.0,
      },
    };

    const alerts = detectCongestionAlerts(mockTrends, rules);
    expect(alerts.length).toBeGreaterThan(0);

    const plazaAlert = alerts[0]!;
    expect(plazaAlert.zoneId).toBe('zone-plaza');
    expect(plazaAlert.severity).toBe('CRITICAL');
    expect(plazaAlert.peakCount).toBe(90);
    expect(plazaAlert.startTime).toBe(2);
    expect(plazaAlert.endTime).toBe(8);
    expect(plazaAlert.duration).toBe(6);
    expect(plazaAlert.exceedPercentage).toBe(13); // (90 - 80) / 80 * 100
  });

  it('evaluates real-time active alerts at current playback time', () => {
    const rules: Record<string, ZoneThresholdRule> = {
      'zone-plaza': {
        zoneId: 'zone-plaza',
        warningThreshold: 50,
        criticalThreshold: 80,
        minDurationSeconds: 1.0,
      },
    };

    const zones = [
      { zone_id: 'zone-plaza', name: 'Quảng Trường', color: '#0072B2' },
    ];

    // Case 1: Count is critical (85 >= 80)
    const readingsCritical: ZoneReading[] = [
      { status: 'COUNTED', count: 85, zoneId: 'zone-plaza', zoneName: 'Quảng Trường' },
    ];
    const critAlerts = checkActiveCongestionAlerts(4.0, readingsCritical, rules, zones);
    expect(critAlerts.length).toBe(1);
    expect(critAlerts[0]!.severity).toBe('CRITICAL');
    expect(critAlerts[0]!.peakCount).toBe(85);

    // Case 2: Count is warning (60 >= 50 and < 80)
    const readingsWarning: ZoneReading[] = [
      { status: 'COUNTED', count: 60, zoneId: 'zone-plaza', zoneName: 'Quảng Trường' },
    ];
    const warnAlerts = checkActiveCongestionAlerts(2.0, readingsWarning, rules, zones);
    expect(warnAlerts.length).toBe(1);
    expect(warnAlerts[0]!.severity).toBe('WARNING');

    // Case 3: Count is safe (30 < 50)
    const readingsSafe: ZoneReading[] = [
      { status: 'COUNTED', count: 30, zoneId: 'zone-plaza', zoneName: 'Quảng Trường' },
    ];
    const safeAlerts = checkActiveCongestionAlerts(0.0, readingsSafe, rules, zones);
    expect(safeAlerts.length).toBe(0);
  });
});
