import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ExecutiveReportModal } from './ExecutiveReportModal';
import { computeSessionReportData } from './reportUtils';
import type { SessionMetadata } from '@/features/review/ReviewWorkspace';
import type { ZoneTrendLine, QualityInterval, NoteMarker } from '@/features/timeline/UnifiedTimeline';

const mockSession: SessionMetadata = {
  sessionId: 'test-session-report-01',
  sourceId: 'video-01',
  mediaName: 'crowd_plaza.mp4',
  duration: 45,
  imageWidth: 1920,
  imageHeight: 1080,
  synthetic: false,
  modelProfileId: 'yolo11s',
  modelProfileSha256: 'sha256-profile',
  checkpointSha256: 'sha256-checkpoint',
  videoSrc: '/sample.mp4',
};

const mockZones = [
  { zone_id: 'zone-1', name: 'Khu vực A (Cổng vào)', color: '#0072B2' },
  { zone_id: 'zone-2', name: 'Khu vực B (Quảng trường)', color: '#009E73' },
];

const mockTrends: ZoneTrendLine[] = [
  {
    zoneId: 'zone-1',
    name: 'Khu vực A (Cổng vào)',
    color: '#0072B2',
    points: [
      { time: 0, count: 5 },
      { time: 20, count: 15 },
      { time: 40, count: 8 },
    ],
  },
  {
    zoneId: 'zone-2',
    name: 'Khu vực B (Quảng trường)',
    color: '#009E73',
    points: [
      { time: 0, count: 3 },
      { time: 20, count: 6 },
      { time: 40, count: 4 },
    ],
  },
];

const mockQualityIntervals: QualityInterval[] = [
  { startTime: 0, endTime: 45, quality: 'VALID' },
];

const mockNotes: NoteMarker[] = [
  { id: 'note-1', time: 10, text: 'Lượng khách tập trung đông tại cổng vào' },
];

describe('ExecutiveReportModal', () => {
  it('renders report document overview with KPIs and zone comparison table', () => {
    const reportData = computeSessionReportData(
      mockSession,
      mockZones,
      mockTrends,
      mockQualityIntervals,
      mockNotes
    );

    render(
      <ExecutiveReportModal
        isOpen={true}
        onClose={vi.fn()}
        reportData={reportData}
      />
    );

    // Title and metadata
    expect(screen.getByText(/Báo Cáo Phân Tích & Giám Sát Đám Đông/i)).toBeInTheDocument();
    expect(screen.getByText('crowd_plaza.mp4')).toBeInTheDocument();

    // KPIs
    expect(screen.getByText('Đỉnh Quan Sát')).toBeInTheDocument();
    expect(screen.getByText('15')).toBeInTheDocument(); // Peak count in zone-1

    // Zone names in table and surge events
    expect(screen.getAllByText('Khu vực A (Cổng vào)').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Khu vực B (Quảng trường)').length).toBeGreaterThan(0);

    // Operator Notes
    expect(screen.getByText('Lượng khách tập trung đông tại cổng vào')).toBeInTheDocument();
  });

  it('switches to multi-zone comparison tab and renders trendlines', () => {
    const reportData = computeSessionReportData(
      mockSession,
      mockZones,
      mockTrends,
      mockQualityIntervals,
      mockNotes
    );

    render(
      <ExecutiveReportModal
        isOpen={true}
        onClose={vi.fn()}
        reportData={reportData}
      />
    );

    const comparisonTabBtn = screen.getByRole('button', { name: /So sánh đa vùng/i });
    fireEvent.click(comparisonTabBtn);

    expect(screen.getByText(/Đồ Thị Xu Hướng Biến Thiên Đa Vùng Theo Thời Gian/i)).toBeInTheDocument();
    expect(screen.getAllByText(/thị phần/i).length).toBeGreaterThan(0);
  });

  it('calls onClose when "Quay lại màn cũ" button is clicked and on Escape key', () => {
    const reportData = computeSessionReportData(
      mockSession,
      mockZones,
      mockTrends,
      mockQualityIntervals,
      mockNotes
    );
    const onClose = vi.fn();

    render(
      <ExecutiveReportModal
        isOpen={true}
        onClose={onClose}
        reportData={reportData}
      />
    );

    // Click back button in header or footer
    const backButtons = screen.getAllByRole('button', { name: /Quay lại/i });
    expect(backButtons.length).toBeGreaterThan(0);
    fireEvent.click(backButtons[0]!);
    expect(onClose).toHaveBeenCalledTimes(1);

    // Escape key
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
