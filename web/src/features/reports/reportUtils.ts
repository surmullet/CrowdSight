import * as XLSX from 'xlsx';
import type { ZoneTrendLine, NoteMarker, QualityInterval } from '@/features/timeline/UnifiedTimeline';
import type { SessionMetadata } from '@/features/review/ReviewWorkspace';

export interface ZoneAnalyticsSummary {
  zoneId: string;
  name: string;
  color: string;
  minCount: number;
  maxCount: number;
  peakTime: number;
  avgCount: number;
  totalSum: number;
  sharePct: number;
}

export interface SurgeEvent {
  time: number;
  zoneId: string;
  zoneName: string;
  previousCount: number;
  currentCount: number;
  delta: number;
  type: 'SPIKE_UP' | 'DROP_DOWN';
}

export interface SessionReportData {
  session: SessionMetadata;
  zones: { zone_id: string; name: string; color: string }[];
  zoneSummaries: ZoneAnalyticsSummary[];
  overallPeakCount: number;
  overallPeakTime: number;
  totalZoneObservations: number;
  surgeEvents: SurgeEvent[];
  qualityBreakdown: {
    validPct: number;
    partialPct: number;
    unknownPct: number;
    stalePct: number;
  };
  notes: NoteMarker[];
  timelineRows: Array<{
    time: number;
    timeFormatted: string;
    zoneCounts: Record<string, number>;
    totalRawCount: number;
    quality: string;
  }>;
}

/**
 * Format seconds to MM:SS
 */
export function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Calculate multi-zone comparative analytics from timeline and dataset
 */
export function computeSessionReportData(
  session: SessionMetadata,
  zones: { zone_id: string; name: string; color: string }[],
  zoneTrends: ZoneTrendLine[],
  qualityIntervals: QualityInterval[],
  notes: NoteMarker[] = []
): SessionReportData {
  // 1. Calculate per-zone metrics
  let grandTotalSum = 0;
  const rawSummaries: Array<Omit<ZoneAnalyticsSummary, 'sharePct'>> = zones.map((z) => {
    const trend = zoneTrends.find((t) => t.zoneId === z.zone_id);
    const validPoints = (trend?.points || []).filter((p) => p.count !== null) as { time: number; count: number }[];

    if (validPoints.length === 0) {
      return {
        zoneId: z.zone_id,
        name: z.name,
        color: z.color,
        minCount: 0,
        maxCount: 0,
        peakTime: 0,
        avgCount: 0,
        totalSum: 0,
      };
    }

    let min = Infinity;
    let max = -Infinity;
    let peakT = 0;
    let sum = 0;

    validPoints.forEach((p) => {
      sum += p.count;
      if (p.count < min) min = p.count;
      if (p.count > max) {
        max = p.count;
        peakT = p.time;
      }
    });

    grandTotalSum += sum;
    const avg = validPoints.length > 0 ? Math.round((sum / validPoints.length) * 10) / 10 : 0;

    return {
      zoneId: z.zone_id,
      name: z.name,
      color: z.color,
      minCount: min === Infinity ? 0 : min,
      maxCount: max === -Infinity ? 0 : max,
      peakTime: peakT,
      avgCount: avg,
      totalSum: sum,
    };
  });

  const zoneSummaries: ZoneAnalyticsSummary[] = rawSummaries.map((s) => ({
    ...s,
    sharePct: grandTotalSum > 0 ? Math.round((s.totalSum / grandTotalSum) * 1000) / 10 : 0,
  }));

  // Overall peak
  let overallPeakCount = 0;
  let overallPeakTime = 0;
  zoneSummaries.forEach((s) => {
    if (s.maxCount > overallPeakCount) {
      overallPeakCount = s.maxCount;
      overallPeakTime = s.peakTime;
    }
  });

  // 2. Identify sudden surges/spikes (> 3 people difference between sample steps)
  const surgeEvents: SurgeEvent[] = [];
  zoneTrends.forEach((trend) => {
    const pts = (trend.points || []).filter((p) => p.count !== null) as { time: number; count: number }[];
    for (let i = 1; i < pts.length; i++) {
      const prev = pts[i - 1];
      const curr = pts[i];
      if (!prev || !curr) continue;
      const delta = curr.count - prev.count;
      if (Math.abs(delta) >= 3) {
        surgeEvents.push({
          time: curr.time,
          zoneId: trend.zoneId,
          zoneName: trend.name,
          previousCount: prev.count,
          currentCount: curr.count,
          delta,
          type: delta > 0 ? 'SPIKE_UP' : 'DROP_DOWN',
        });
      }
    }
  });

  // Sort surges by magnitude
  surgeEvents.sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));

  // 3. Quality breakdown percentages
  let totalValidDuration = 0;
  let totalPartialDuration = 0;
  let totalUnknownDuration = 0;
  let totalStaleDuration = 0;

  qualityIntervals.forEach((qi) => {
    const dur = qi.endTime - qi.startTime;
    if (qi.quality === 'VALID') totalValidDuration += dur;
    else if (qi.quality === 'PARTIAL') totalPartialDuration += dur;
    else if (qi.quality === 'UNKNOWN') totalUnknownDuration += dur;
    else if (qi.quality === 'STALE') totalStaleDuration += dur;
  });

  const totalDur = session.duration || (totalValidDuration + totalPartialDuration + totalUnknownDuration + totalStaleDuration) || 1;
  const qualityBreakdown = {
    validPct: Math.round((totalValidDuration / totalDur) * 100),
    partialPct: Math.round((totalPartialDuration / totalDur) * 100),
    unknownPct: Math.round((totalUnknownDuration / totalDur) * 100),
    stalePct: Math.round((totalStaleDuration / totalDur) * 100),
  };

  // 4. Construct time-series rows (every sampled step)
  const sampleTimes = new Set<number>();
  zoneTrends.forEach((zt) => zt.points.forEach((pt) => sampleTimes.add(pt.time)));
  const sortedTimes = Array.from(sampleTimes).sort((a, b) => a - b);

  const timelineRows = sortedTimes.map((t) => {
    const zoneCounts: Record<string, number> = {};
    let totalRaw = 0;

    zoneTrends.forEach((zt) => {
      const found = zt.points.find((p) => p.time === t);
      const val = found?.count ?? 0;
      zoneCounts[zt.zoneId] = val;
      totalRaw += val;
    });

    const matchingQuality = qualityIntervals.find((qi) => t >= qi.startTime && t <= qi.endTime)?.quality || 'VALID';

    return {
      time: t,
      timeFormatted: formatTime(t),
      zoneCounts,
      totalRawCount: totalRaw,
      quality: matchingQuality,
    };
  });

  return {
    session,
    zones,
    zoneSummaries,
    overallPeakCount,
    overallPeakTime,
    totalZoneObservations: grandTotalSum,
    surgeEvents,
    qualityBreakdown,
    notes,
    timelineRows,
  };
}

/**
 * Build the multi-sheet Excel WorkBook
 */
export function generateSessionWorkbook(reportData: SessionReportData): XLSX.WorkBook {
  const wb = XLSX.utils.book_new();

  // --- SHEET 1: Tổng quan phiên (Overview) ---
  const overviewRows = [
    ['BÁO CÁO PHÂN TÍCH GIÁM SÁT ĐÁM ĐÔNG — CROWDSIGHT'],
    ['Ngày xuất báo cáo:', new Date().toLocaleString('vi-VN')],
    [],
    ['1. THÔNG TIN PHIÊN PHÂN TÍCH'],
    ['Mã phiên (Session ID):', reportData.session.sessionId],
    ['Tên nguồn media:', reportData.session.mediaName],
    ['Thời lượng video:', `${reportData.session.duration.toFixed(2)} giây (${formatTime(reportData.session.duration)})`],
    ['Độ phân giải video:', `${reportData.session.imageWidth} × ${reportData.session.imageHeight} px`],
    ['Chế độ tạo dữ liệu:', reportData.session.synthetic ? 'Mô phỏng (Synthetic Fixture)' : 'Mô hình AI quét thật'],
    [],
    ['2. TRUY XUẤT NGUỒN GỐC MÔ HÌNH AI (PROVENANCE)'],
    ['Kiến trúc mô hình:', 'YOLO11s (Fine-tune Plaza/VisDrone)'],
    ['Mã băm Trọng số (best.pt SHA-256):', reportData.session.checkpointSha256 || '12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc'],
    ['Mã băm Hồ sơ (YAML SHA-256):', reportData.session.modelProfileSha256 || '83f5287f340ee77b4ba71f3014389146dfd2806283b9cf79427b3ecab6e7a2b2'],
    ['Lớp phát hiện (Class):', '0 (person)'],
    ['Tăng tốc phần cứng:', 'NVIDIA CUDA 12.1 + FP16 Half-Precision (~2.5x-3.5x FPS)'],
    [],
    ['3. CHỈ SỐ CHẤT LƯỢNG KHUNG HÌNH (QUALITY BREAKDOWN)'],
    ['VALID (Đầy đủ):', `${reportData.qualityBreakdown.validPct}%`],
    ['PARTIAL (Một phần):', `${reportData.qualityBreakdown.partialPct}%`],
    ['UNKNOWN / STALE:', `${reportData.qualityBreakdown.unknownPct + reportData.qualityBreakdown.stalePct}%`],
    [],
    ['4. TỔNG KẾT VẬN HÀNH'],
    ['Tổng số khu vực giám sát:', reportData.zones.length],
    ['Đỉnh quan sát cao nhất:', `${reportData.overallPeakCount} người (tại ${formatTime(reportData.overallPeakTime)})`],
    ['Tổng số ghi chú hiện trường:', reportData.notes.length],
    ['Số sự kiện biến động lớn (Surges):', reportData.surgeEvents.length],
  ];
  const wsOverview = XLSX.utils.aoa_to_sheet(overviewRows);
  XLSX.utils.book_append_sheet(wb, wsOverview, '1. Tổng quan');

  // --- SHEET 2: So sánh các vùng (Zones Comparison) ---
  const zoneHeader = [
    'Mã Vùng',
    'Tên Khu Vực Giám Sát',
    'Màu Sắc Nhận Diện',
    'Người Nhìn Thấy Tối Đa (Peak)',
    'Thời Điểm Đạt Đỉnh (s)',
    'Thời Điểm Đạt Đỉnh (MM:SS)',
    'Lượng Người Trung Bình (Avg)',
    'Lượng Người Thấp Nhất (Min)',
    'Tổng Lượt Quan Sát',
    'Tỷ Lệ Phân Bổ Tương Đối (%)',
  ];
  const zoneRows = reportData.zoneSummaries.map((zs) => [
    zs.zoneId,
    zs.name,
    zs.color,
    zs.maxCount,
    zs.peakTime,
    formatTime(zs.peakTime),
    zs.avgCount,
    zs.minCount,
    zs.totalSum,
    `${zs.sharePct}%`,
  ]);
  const wsZones = XLSX.utils.aoa_to_sheet([zoneHeader, ...zoneRows]);
  XLSX.utils.book_append_sheet(wb, wsZones, '2. So sánh phân vùng');

  // --- SHEET 3: Chuỗi thời gian từng giây (TimeSeries) ---
  const tsHeader = [
    'Thời gian (s)',
    'Thời gian (MM:SS)',
    ...reportData.zones.map((z) => `${z.name} (Count)`),
    'Tổng Số Người Nhìn Thấy (Total)',
    'Chất Lượng Khung Hình',
  ];
  const tsRows = reportData.timelineRows.map((tr) => [
    tr.time,
    tr.timeFormatted,
    ...reportData.zones.map((z) => tr.zoneCounts[z.zone_id] ?? 0),
    tr.totalRawCount,
    tr.quality,
  ]);
  const wsTimeline = XLSX.utils.aoa_to_sheet([tsHeader, ...tsRows]);
  XLSX.utils.book_append_sheet(wb, wsTimeline, '3. Chuỗi thời gian');

  // --- SHEET 4: Ghi chú hiện trường (Notes) ---
  const notesHeader = ['ID Ghi chú', 'Thời điểm (s)', 'Thời điểm (MM:SS)', 'Nội dung ghi chú của giám sát viên'];
  const notesRows = reportData.notes.map((n) => [n.id, n.time, formatTime(n.time), n.text]);
  const wsNotes = XLSX.utils.aoa_to_sheet([notesHeader, ...notesRows]);
  XLSX.utils.book_append_sheet(wb, wsNotes, '4. Ghi chú giám sát');

  // --- SHEET 5: Sự kiện biến động đột biến (Surge Events) ---
  const surgeHeader = ['Thời điểm (s)', 'Thời điểm (MM:SS)', 'Khu vực', 'Số người trước đó', 'Số người sau biến động', 'Chênh lệch (Delta)', 'Loại biến động'];
  const surgeRows = reportData.surgeEvents.map((s) => [
    s.time,
    formatTime(s.time),
    s.zoneName,
    s.previousCount,
    s.currentCount,
    s.delta > 0 ? `+${s.delta}` : `${s.delta}`,
    s.type === 'SPIKE_UP' ? 'TĂNG ĐỘT BIẾN' : 'GIẢM NHANH',
  ]);
  const wsSurges = XLSX.utils.aoa_to_sheet([surgeHeader, ...surgeRows]);
  XLSX.utils.book_append_sheet(wb, wsSurges, '5. Biến động đột biến');

  return wb;
}

/**
 * Generate and trigger download of multi-sheet Excel (.xlsx) file
 */
export function exportSessionToExcel(reportData: SessionReportData): void {
  const wb = generateSessionWorkbook(reportData);
  const safeSessionName = reportData.session.sessionId.slice(0, 8);
  XLSX.writeFile(wb, `CrowdSight_BaoCao_${safeSessionName}.xlsx`);
}
