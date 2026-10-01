/**
 * Bilingual localization dictionaries (Vietnamese default + English).
 * Strictly enforces non-alarmist, scientifically honest crowd observation terminology.
 */

export type Locale = 'vi' | 'en';

export const translations = {
  vi: {
    appTitle: 'CrowdSight — Giám Sát Đám Đông Trên Video',
    appSubtitle: 'Giám sát đám đông video',
    nav: {
      sessions: 'Thư viện',
      wizard: 'Tạo phiên',
      zones: 'Soạn vùng',
      model: 'Mô hình',
      devStates: '/dev/states',
      switchLanguage: 'Đổi sang English',
    },
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
    sessions: {
      title: 'Thư viện phiên phân tích',
      subtitle: 'Quản lý các bản ghi video giám sát đám đông đã phân tích và lưu trữ',
      newSession: 'Bắt đầu phân tích mới',
      searchPlaceholder: 'Tìm theo tên video, mã phiên, tập vùng...',
      filters: {
        all: 'Tất cả',
        completed: 'Hoàn tất',
        active: 'Đang xử lý',
        failed: 'Thất bại',
        cancelled: 'Đã hủy',
      },
      emptyTitle: 'Không tìm thấy phiên phân tích nào',
      emptySubtitle: 'Hãy tạo phiên mới hoặc điều chỉnh bộ lọc tìm kiếm.',
      deleteConfirmTitle: 'Xác nhận xóa phiên phân tích',
      deleteConfirmWarning: 'Cảnh báo: Hành động này sẽ xóa vĩnh viễn toàn bộ tệp kết quả quan sát và dữ liệu suy luận liên kết.',
      cancel: 'Hủy bỏ',
      delete: 'Xóa vĩnh viễn',
    },
  },
  en: {
    appTitle: 'CrowdSight — Recorded Video Crowd Monitoring',
    appSubtitle: 'Recorded video crowd monitoring',
    nav: {
      sessions: 'Library',
      wizard: 'New Session',
      zones: 'Zone Editor',
      model: 'Model Status',
      devStates: '/dev/states',
      switchLanguage: 'Đổi sang Tiếng Việt',
    },
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
    sessions: {
      title: 'Analysis Session Library',
      subtitle: 'Manage analyzed and archived crowd surveillance video records',
      newSession: 'Start New Analysis',
      searchPlaceholder: 'Search by video name, session ID, zone set...',
      filters: {
        all: 'All',
        completed: 'Completed',
        active: 'Active',
        failed: 'Failed',
        cancelled: 'Cancelled',
      },
      emptyTitle: 'No analysis sessions found',
      emptySubtitle: 'Create a new session or adjust your search filter.',
      deleteConfirmTitle: 'Confirm session deletion',
      deleteConfirmWarning: 'Warning: This will permanently delete all observation result artifacts and associated inference data.',
      cancel: 'Cancel',
      delete: 'Delete Permanently',
    },
  },
} as const;

export type TranslationKey = keyof typeof translations.vi;

type DeepStringRecord<T> = {
  [K in keyof T]: T[K] extends object ? DeepStringRecord<T[K]> : string;
};

export type TranslationDictionary = DeepStringRecord<typeof translations.vi>;
