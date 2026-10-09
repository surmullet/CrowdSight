import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CongestionAlertBanner } from './CongestionAlertBanner';
import type { CongestionAlertEvent } from './alertUtils';

describe('CongestionAlertBanner', () => {
  const mockAlertWarning: CongestionAlertEvent = {
    id: 'alert-zone-1-10.0',
    zoneId: 'zone-1',
    zoneName: 'Khu vực Sảnh Chính',
    zoneColor: '#FF5733',
    severity: 'WARNING',
    startTime: 10.0,
    endTime: 15.0,
    peakCount: 45,
    threshold: 40,
    duration: 5.0,
    exceedPercentage: 13,
  };

  const mockAlertCritical: CongestionAlertEvent = {
    id: 'alert-zone-2-12.0',
    zoneId: 'zone-2',
    zoneName: 'Khu vực Cửa Ra',
    zoneColor: '#C70039',
    severity: 'CRITICAL',
    startTime: 12.0,
    endTime: 20.0,
    peakCount: 85,
    threshold: 60,
    duration: 8.0,
    exceedPercentage: 42,
  };

  it('renders nothing when alerts array is empty', () => {
    const { container } = render(<CongestionAlertBanner alerts={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders warning banner with zone details', () => {
    render(<CongestionAlertBanner alerts={[mockAlertWarning]} />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/Cảnh Báo Ngưỡng Vàng/i)).toBeInTheDocument();
    expect(screen.getByText('Khu vực Sảnh Chính')).toBeInTheDocument();
    expect(screen.getByText(/45 người/i)).toBeInTheDocument();
    expect(screen.getByText(/Vượt ngưỡng định mức 40 người/i)).toBeInTheDocument();
  });

  it('prioritizes critical banner and shows multi-zone badge when multiple alerts exist', () => {
    render(
      <CongestionAlertBanner
        alerts={[mockAlertWarning, mockAlertCritical]}
      />
    );

    expect(screen.getByText(/Báo Động Quá Tải Đỏ/i)).toBeInTheDocument();
    expect(screen.getByText('Khu vực Cửa Ra')).toBeInTheDocument();
    expect(screen.getByText(/85 người/i)).toBeInTheDocument();
    expect(screen.getByText(/\+1 khu vực khác/i)).toBeInTheDocument();
  });

  it('calls onSeek when "Tua tới mốc này" is clicked', () => {
    const onSeek = vi.fn();
    render(
      <CongestionAlertBanner
        alerts={[mockAlertCritical]}
        onSeek={onSeek}
      />
    );

    const seekBtn = screen.getByRole('button', { name: /Tua tới mốc này/i });
    fireEvent.click(seekBtn);
    expect(onSeek).toHaveBeenCalledWith(12.0);
  });

  it('calls onOpenAlertsTab when "Chi tiết cảnh báo" is clicked', () => {
    const onOpenAlertsTab = vi.fn();
    render(
      <CongestionAlertBanner
        alerts={[mockAlertCritical]}
        onOpenAlertsTab={onOpenAlertsTab}
      />
    );

    const detailsBtn = screen.getByRole('button', { name: /Chi tiết cảnh báo/i });
    fireEvent.click(detailsBtn);
    expect(onOpenAlertsTab).toHaveBeenCalled();
  });

  it('calls onDismiss when close button is clicked', () => {
    const onDismiss = vi.fn();
    render(
      <CongestionAlertBanner
        alerts={[mockAlertCritical]}
        onDismiss={onDismiss}
      />
    );

    const dismissBtn = screen.getByRole('button', { name: /Đóng thông báo/i });
    fireEvent.click(dismissBtn);
    expect(onDismiss).toHaveBeenCalled();
  });
});
