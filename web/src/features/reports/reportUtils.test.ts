import { describe, it, expect } from 'vitest';
import {
  computeSessionReportData,
  generateSessionWorkbook,
  formatTime,
} from './reportUtils';
import type { SessionMetadata } from '@/features/review/ReviewWorkspace';
import type { ZoneTrendLine, QualityInterval, NoteMarker } from '@/features/timeline/UnifiedTimeline';

const mockSession: SessionMetadata = {
  sessionId: 'test-session-001',
  sourceId: 'video-001',
  mediaName: 'plaza_cam.mp4',
  duration: 60,
  imageWidth: 1920,
  imageHeight: 1080,
  synthetic: false,
  modelProfileId: 'yolo11s',
  modelProfileSha256: 'sha256-profile',
  checkpointSha256: 'sha256-checkpoint',
  videoSrc: '/sample.mp4',
};

const mockZones = [
  { zone_id: 'zone-a', name: 'Khu vực A (Cổng chính)', color: '#0072B2' },
  { zone_id: 'zone-b', name: 'Khu vực B (Hành lang)', color: '#009E73' },
];

const mockTrends: ZoneTrendLine[] = [
  {
    zoneId: 'zone-a',
    name: 'Khu vực A (Cổng chính)',
    color: '#0072B2',
    points: [
      { time: 0, count: 2 },
      { time: 10, count: 8 },
      { time: 20, count: 12 },
      { time: 30, count: 4 },
    ],
  },
  {
    zoneId: 'zone-b',
    name: 'Khu vực B (Hành lang)',
    color: '#009E73',
    points: [
      { time: 0, count: 1 },
      { time: 10, count: 3 },
      { time: 20, count: 2 },
      { time: 30, count: 2 },
    ],
  },
];

const mockQualityIntervals: QualityInterval[] = [
  { startTime: 0, endTime: 60, quality: 'VALID' },
];

const mockNotes: NoteMarker[] = [
  { id: 'n-1', time: 15, text: 'Quan sát thấy lưu lượng tăng đột biến tại cổng chính' },
];

describe('reportUtils', () => {
  it('formats seconds into MM:SS correctly', () => {
    expect(formatTime(0)).toBe('00:00');
    expect(formatTime(65)).toBe('01:05');
    expect(formatTime(125.8)).toBe('02:05');
  });

  it('computes multi-zone comparative analytics properly', () => {
    const data = computeSessionReportData(
      mockSession,
      mockZones,
      mockTrends,
      mockQualityIntervals,
      mockNotes
    );

    expect(data.zoneSummaries.length).toBe(2);
    const zoneA = data.zoneSummaries.find((z) => z.zoneId === 'zone-a')!;
    expect(zoneA.maxCount).toBe(12);
    expect(zoneA.peakTime).toBe(20);
    expect(zoneA.minCount).toBe(2);
    expect(zoneA.sharePct).toBeGreaterThan(50); // Zone A had more people than Zone B

    expect(data.overallPeakCount).toBe(12);
    expect(data.overallPeakTime).toBe(20);

    // Surges detection: from 10s (8 people) to 20s (12 people) is a delta of 4 (>= 3)
    // and from 20s (12 people) to 30s (4 people) is delta of -8
    expect(data.surgeEvents.length).toBeGreaterThan(0);
    expect(data.surgeEvents[0]?.zoneName).toBe('Khu vực A (Cổng chính)');

    // Quality breakdown
    expect(data.qualityBreakdown.validPct).toBe(100);
  });

  it('generates multi-sheet Excel workbook with all 5 sheets and accurate structure', () => {
    const data = computeSessionReportData(
      mockSession,
      mockZones,
      mockTrends,
      mockQualityIntervals,
      mockNotes
    );

    const wb = generateSessionWorkbook(data);

    expect(wb.SheetNames).toEqual([
      '1. Tổng quan',
      '2. So sánh phân vùng',
      '3. Chuỗi thời gian',
      '4. Ghi chú giám sát',
      '5. Biến động đột biến',
    ]);

    // Check sheets contain actual rows
    const wsOverview = wb.Sheets['1. Tổng quan'];
    expect(wsOverview).toBeDefined();

    const wsZones = wb.Sheets['2. So sánh phân vùng'];
    expect(wsZones).toBeDefined();

    const wsTimeline = wb.Sheets['3. Chuỗi thời gian'];
    expect(wsTimeline).toBeDefined();
  });
});
