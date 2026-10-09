import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CongestionAlertBanner } from './CongestionAlertBanner';
import { CongestionAlertsTab } from './CongestionAlertsTab';
import type { CongestionAlertEvent, ZoneThresholdRule } from './alertUtils';

const mockAlerts: CongestionAlertEvent[] = [
  {
    id: 'alert-1',
    zoneId: 'zone-a',
    zoneName: 'Khu vực A (Cổng vào)',
    zoneColor: '#0072B2',
    severity: 'CRITICAL',
    startTime: 5.0,
    endTime: 12.0,
    peakCount: 125,
    threshold: 80,
    duration: 7.0,
    exceedPercentage: 56,
  },
  {
    id: 'alert-2',
    zoneId: 'zone-b',
    zoneName: 'Khu vực B (Quảng trường)',
    zoneColor: '#009E73',
    severity: 'WARNING',
    startTime: 20.0,
    endTime: 25.0,
    peakCount: 65,
    threshold: 50,
    duration: 5.0,
    exceedPercentage: 30,
  },
];

const mockRules: Record<string, ZoneThresholdRule> = {
  'zone-a': {
    zoneId: 'zone-a',
    warningThreshold: 50,
    criticalThreshold: 80,
    minDurationSeconds: 1.0,
  },
  'zone-b': {
    zoneId: 'zone-b',
    warningThreshold: 40,
    criticalThreshold: 70,
    minDurationSeconds: 1.0,
  },
};

const mockZones = [
  { zone_id: 'zone-a', name: 'Khu vực A (Cổng vào)', color: '#0072B2' },
  { zone_id: 'zone-b', name: 'Khu vực B (Quảng trường)', color: '#009E73' },
];

describe('CongestionAlertBanner', () => {
  it('renders critical alert banner with seek and details action', () => {
    const onSeek = vi.fn();
    const onOpen = vi.fn();

    render(
      <CongestionAlertBanner
        alerts={mockAlerts}
        onSeek={onSeek}
        onOpenAlertsTab={onOpen}
      />
    );

    expect(screen.getByText(/Báo Động Quá Tải Đỏ/i)).toBeInTheDocument();
    expect(screen.getByText('Khu vực A (Cổng vào)')).toBeInTheDocument();
    expect(screen.getByText('125 người')).toBeInTheDocument();

    const seekBtn = screen.getByRole('button', { name: /Tua tới mốc này/i });
    fireEvent.click(seekBtn);
    expect(onSeek).toHaveBeenCalledWith(5.0);

    const detailsBtn = screen.getByRole('button', { name: /Chi tiết cảnh báo/i });
    fireEvent.click(detailsBtn);
    expect(onOpen).toHaveBeenCalled();
  });
});

describe('CongestionAlertsTab', () => {
  it('renders alert events list and filters by severity', () => {
    const onSeek = vi.fn();
    const onUpdateRule = vi.fn();
    const onResetRules = vi.fn();

    render(
      <CongestionAlertsTab
        alerts={mockAlerts}
        thresholdRules={mockRules}
        zones={mockZones}
        onUpdateRule={onUpdateRule}
        onResetRules={onResetRules}
        onSeek={onSeek}
        currentTime={6.0}
      />
    );

    expect(screen.getByText('Giám Sát Quá Tải')).toBeInTheDocument();
    expect(screen.getByText('2 sự kiện')).toBeInTheDocument();

    // Filter by Critical
    const critFilterBtn = screen.getByRole('button', { name: /🚨 Nguy hiểm/i });
    fireEvent.click(critFilterBtn);
    expect(screen.getByText('Khu vực A (Cổng vào)')).toBeInTheDocument();
    expect(screen.queryByText('Khu vực B (Quảng trường)')).not.toBeInTheDocument();

    // Seek button
    const seekBtn = screen.getByRole('button', { name: /Tua tới/i });
    fireEvent.click(seekBtn);
    expect(onSeek).toHaveBeenCalledWith(5.0);
  });

  it('toggles threshold settings and updates rules', () => {
    const onUpdateRule = vi.fn();

    render(
      <CongestionAlertsTab
        alerts={mockAlerts}
        thresholdRules={mockRules}
        zones={mockZones}
        onUpdateRule={onUpdateRule}
        onResetRules={vi.fn()}
        onSeek={vi.fn()}
        currentTime={0}
      />
    );

    const settingsBtn = screen.getByRole('button', { name: /Cấu hình ngưỡng/i });
    fireEvent.click(settingsBtn);

    expect(screen.getByText('Thiết Lập Ngưỡng Quá Tải Từng Khu Vực')).toBeInTheDocument();
  });
});
