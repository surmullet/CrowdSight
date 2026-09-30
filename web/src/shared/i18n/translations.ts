/**
 * Bilingual localization dictionaries (Vietnamese default + English).
 * Strictly enforces non-alarmist, scientifically honest crowd observation terminology.
 */

export type Locale = 'vi' | 'en';

export const translations = {
  vi: {
    appTitle: 'CrowdSight — Giám Sát Đám Đông Trên Video',
    experimentalBanner: 'Thử nghiệm — chưa được duyệt cho vận hành thực tế. Cảnh báo vận hành đang tắt.',
    syntheticBadge: 'Dữ liệu mô phỏng',
    measurementSemanticsLabel: 'Về phép đo này',
    measurementDefinition:
      'Số người nhìn thấy được, do mô hình phát hiện, trong vùng được quan sát. Mô hình có thể đếm thiếu ở cảnh đông. Đây không phải sức chứa hay lượng người tham dự.',
    densityNotice: 'Chưa có mật độ — cần hiệu chuẩn tại hiện trường',
    rawScoreLabel: 'Điểm thô của mô hình (chưa hiệu chuẩn)',
    heatmapDisclaimer: 'Tương đối trong khung hình — không phải mật độ người/m²',
    zones: {
      title: 'Vùng quan sát',
      counted: 'người nhìn thấy',
      zeroAffirmation: '0 người được nhìn thấy — vùng đã quan sát đầy đủ',
      notFullyObserved: 'Chưa quan sát đầy đủ vùng này',
      unknown: 'Không có số liệu đáng tin cậy ở khung hình này',
      stale: 'Số liệu đã cũ',
      partialCoverageBadge: 'Quan sát một phần',
    },
    quality: {
      valid: 'Đầy đủ (VALID)',
      partial: 'Một phần (PARTIAL)',
      unknown: 'Không xác định (UNKNOWN)',
      stale: 'Đã cũ (STALE)',
    },
    reasons: {
      FRAME_BLANK: 'Khung hình bị tối hoặc sáng lóa bất thường',
      FRAME_FROZEN: 'Khung hình bị đóng băng lặp lại',
      DECODE_FAILED: 'Lỗi giải mã luồng video',
      ZONE_OBSCURED: 'Vùng quan sát bị che khuất một phần',
    },
    actions: {
      startAnalysis: 'Bắt đầu phân tích',
      cancelAnalysis: 'Hủy phân tích',
      exportData: 'Xuất dữ liệu',
      viewStates: 'Kiểm tra trạng thái mẫu',
      languageToggle: 'English',
    },
  },
  en: {
    appTitle: 'CrowdSight — Recorded Video Crowd Monitoring',
    experimentalBanner: 'Experimental — not approved for operational use. Operational alerts are disabled.',
    syntheticBadge: 'Simulated Data',
    measurementSemanticsLabel: 'About this measurement',
    measurementDefinition:
      'Visible persons detected by the model within the observed zone. The model may significantly undercount in dense crowds. This is not capacity or attendance.',
    densityNotice: 'Density unavailable — requires site-specific calibration',
    rawScoreLabel: 'Raw model score (uncalibrated)',
    heatmapDisclaimer: 'Relative in image space — not metric people/m²',
    zones: {
      title: 'Monitored Zones',
      counted: 'visible people',
      zeroAffirmation: '0 people observed — zone fully observed',
      notFullyObserved: 'Zone not fully observed in this frame',
      unknown: 'No reliable data for this frame',
      stale: 'Data is stale',
      partialCoverageBadge: 'Partial observation',
    },
    quality: {
      valid: 'Valid',
      partial: 'Partial',
      unknown: 'Unknown',
      stale: 'Stale',
    },
    reasons: {
      FRAME_BLANK: 'Frame is blank, blackout, or whiteout',
      FRAME_FROZEN: 'Repeated frozen frame detected',
      DECODE_FAILED: 'Failed to decode video frame',
      ZONE_OBSCURED: 'Zone is partially obscured',
    },
    actions: {
      startAnalysis: 'Start Analysis',
      cancelAnalysis: 'Cancel Analysis',
      exportData: 'Export Data',
      viewStates: 'Inspect Sample States',
      languageToggle: 'Tiếng Việt',
    },
  },
} as const;

export type TranslationKey = keyof typeof translations.vi;
