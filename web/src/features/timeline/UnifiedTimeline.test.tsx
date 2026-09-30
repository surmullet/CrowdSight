import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { UnifiedTimeline } from './UnifiedTimeline';

describe('UnifiedTimeline', () => {
  it('renders slider element with accessibility attributes', () => {
    const onSeek = vi.fn();
    render(
      <UnifiedTimeline
        duration={60}
        currentTime={15}
        qualityIntervals={[
          { startTime: 0, endTime: 30, quality: 'VALID' },
          { startTime: 30, endTime: 60, quality: 'PARTIAL' },
        ]}
        zoneTrends={[]}
        onSeek={onSeek}
      />
    );

    const slider = screen.getByRole('slider');
    expect(slider).toBeInTheDocument();
    expect(slider).toHaveAttribute('aria-valuemin', '0');
    expect(slider).toHaveAttribute('aria-valuemax', '60');
    expect(slider).toHaveAttribute('aria-valuenow', '15');
  });

  it('displays warning indicator when missingFramesCount > 0', () => {
    render(
      <UnifiedTimeline
        duration={60}
        currentTime={0}
        qualityIntervals={[]}
        zoneTrends={[]}
        missingFramesCount={12}
        onSeek={vi.fn()}
      />
    );

    expect(
      screen.getByText(/12 khung không có số liệu/i)
    ).toBeInTheDocument();
  });

  it('renders SVG path with gaps when count is null', () => {
    const { container } = render(
      <UnifiedTimeline
        duration={10}
        currentTime={5}
        qualityIntervals={[]}
        zoneTrends={[
          {
            zoneId: 'z1',
            name: 'Zone A',
            color: '#0072B2',
            points: [
              { time: 0, count: 5 },
              { time: 2, count: null }, // Gap!
              { time: 4, count: 8 },
            ],
          },
        ]}
        onSeek={vi.fn()}
      />
    );

    const path = container.querySelector('svg path');
    expect(path).toBeInTheDocument();
    const d = path?.getAttribute('d') ?? '';
    // Since index 1 has count: null, the path must have separate M commands for subpaths
    const mCount = (d.match(/M/g) || []).length;
    expect(mCount).toBe(2);
  });
});
