import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { PlayerControls, formatMediaTime } from './PlayerControls';
import { usePlaybackStore } from '@/shared/state/playbackStore';

describe('PlayerControls', () => {
  it('formats media time correctly with hundredths', () => {
    expect(formatMediaTime(0)).toBe('00:00.00');
    expect(formatMediaTime(4.2)).toBe('00:04.20');
    expect(formatMediaTime(65.05)).toBe('01:05.05');
    expect(formatMediaTime(3600)).toBe('60:00.00');
  });

  it('renders playback buttons and time labels', () => {
    usePlaybackStore.setState({
      currentTime: 10.5,
      duration: 120.0,
      isPlaying: false,
      playbackRate: 1.0,
    });

    render(<PlayerControls />);

    expect(screen.getByRole('button', { name: 'Phát' })).toBeInTheDocument();
    expect(screen.getByText('00:10.50')).toBeInTheDocument();
    expect(screen.getByText('02:00.00')).toBeInTheDocument();
  });

  it('cycles playback rate when speed button is clicked', () => {
    usePlaybackStore.setState({ playbackRate: 1.0 });
    render(<PlayerControls />);

    const rateBtn = screen.getByRole('button', { name: /Tốc độ phát hiện tại: 1x/i });
    fireEvent.click(rateBtn);
    expect(usePlaybackStore.getState().playbackRate).toBe(2.0);

    fireEvent.click(rateBtn);
    expect(usePlaybackStore.getState().playbackRate).toBe(0.5);
  });

  it('toggles boxes, zones, and heatmap layers', () => {
    usePlaybackStore.setState({
      showBoxes: true,
      showZones: true,
      showHeatmap: false,
    });

    render(<PlayerControls />);

    const boxesBtn = screen.getByRole('button', { name: /Boxes/i });
    const zonesBtn = screen.getByRole('button', { name: /Zones/i });
    const heatmapBtn = screen.getByRole('button', { name: /Heat map/i });

    expect(boxesBtn).toHaveAttribute('aria-pressed', 'true');
    expect(zonesBtn).toHaveAttribute('aria-pressed', 'true');
    expect(heatmapBtn).toHaveAttribute('aria-pressed', 'false');

    fireEvent.click(boxesBtn);
    expect(usePlaybackStore.getState().showBoxes).toBe(false);

    fireEvent.click(heatmapBtn);
    expect(usePlaybackStore.getState().showHeatmap).toBe(true);
  });
});
