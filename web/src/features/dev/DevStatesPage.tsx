import React, { useState } from 'react';
import type { ZoneReading, FrameQuality } from '@/shared/types/domain';
import { Banner } from '@/shared/ui/Banner';
import { QualityBadge } from '@/shared/ui/QualityBadge';
import { ZoneCard } from '@/shared/ui/ZoneCard';
import { SemanticsModal } from '@/shared/ui/SemanticsModal';
import { Languages, ArrowLeft } from 'lucide-react';
import { useLanguage, LanguageWrapper } from '@/shared/i18n/LanguageContext';

interface FixtureScenario {
  id: string;
  nameVi: string;
  nameEn: string;
  quality: FrameQuality;
  descriptionVi: string;
  descriptionEn: string;
  readings: ZoneReading[];
  isSynthetic?: boolean;
}

const DevStatesPageContent: React.FC<{ onBack?: () => void }> = ({ onBack }) => {
  const { locale, toggleLocale } = useLanguage();
  const [showSemantics, setShowSemantics] = useState<boolean>(false);

  const fixtures: FixtureScenario[] = [
    {
      id: 'fixture-1-valid',
      nameVi: '1. Khung hình VALID (Có người nhìn thấy)',
      nameEn: '1. VALID Frame (Visible detections)',
      quality: 'VALID',
      descriptionVi: 'Mọi zone quan sát đầy đủ, phát hiện 14 người ở Lối vào và 5 người ở Sảnh.',
      descriptionEn: 'All zones fully observed, detecting 14 persons in Entrance and 5 in Lobby.',
      readings: [
        { status: 'COUNTED', count: 14, zoneId: 'zone_entrance', zoneName: 'Lối vào chính (Zone A)' },
        { status: 'COUNTED', count: 5, zoneId: 'zone_lobby', zoneName: 'Khu sảnh đợi (Zone B)' },
      ],
    },
    {
      id: 'fixture-2-valid-zero',
      nameVi: '2. Khung hình VALID (0 người nhìn thấy)',
      nameEn: '2. VALID Frame (0 visible persons)',
      quality: 'VALID',
      descriptionVi: 'Vùng được quan sát đầy đủ nhưng không có người. Khẳng định số 0 rõ ràng.',
      descriptionEn: 'Zone fully observed with zero detections. Distinct affirmative zero presentation.',
      readings: [
        { status: 'COUNTED', count: 0, zoneId: 'zone_entrance', zoneName: 'Lối vào chính (Zone A)' },
        { status: 'COUNTED', count: 0, zoneId: 'zone_lobby', zoneName: 'Khu sảnh đợi (Zone B)' },
      ],
    },
    {
      id: 'fixture-3-partial',
      nameVi: '3. Khung hình PARTIAL (Quan sát một phần)',
      nameEn: '3. PARTIAL Frame (Subset of zones observed)',
      quality: 'PARTIAL',
      descriptionVi: 'Chỉ Lối vào được quan sát đủ. Khu vực Cầu thang bị che khuất -> KHÔNG CÓ SỐ LIỆU (không được hiện 0).',
      descriptionEn: 'Only Entrance is fully observed. Stairs zone is obscured -> UNAVAILABLE (never 0).',
      readings: [
        {
          status: 'COUNTED',
          count: 8,
          zoneId: 'zone_entrance',
          zoneName: 'Lối vào chính (Zone A)',
          isPartialObservation: true,
        },
        {
          status: 'NOT_FULLY_OBSERVED',
          zoneId: 'zone_stairs',
          zoneName: 'Khu vực cầu thang (Zone C)',
        },
      ],
    },
    {
      id: 'fixture-4-unknown',
      nameVi: '4. Khung hình UNKNOWN (Không có bằng chứng tin cậy)',
      nameEn: '4. UNKNOWN Frame (Unusable visual evidence)',
      quality: 'UNKNOWN',
      descriptionVi: 'Khung hình bị tối hoặc lỗi giải mã -> KHÔNG CÓ SỐ LIỆU ĐẾM (tuyệt đối không hiển thị 0).',
      descriptionEn: 'Blank frame or decode error -> COUNT UNAVAILABLE (strictly never defaults to 0).',
      readings: [
        {
          status: 'UNKNOWN',
          zoneId: 'zone_entrance',
          zoneName: 'Lối vào chính (Zone A)',
          reasonCode: 'FRAME_BLANK',
        },
        {
          status: 'UNKNOWN',
          zoneId: 'zone_lobby',
          zoneName: 'Khu sảnh đợi (Zone B)',
          reasonCode: 'FRAME_BLANK',
        },
      ],
    },
    {
      id: 'fixture-5-stale',
      nameVi: '5. Khung hình STALE (Số liệu đã cũ)',
      nameEn: '5. STALE Frame (Evidence gap exceeded)',
      quality: 'STALE',
      descriptionVi: 'Khoảng cách thời gian vượt ngưỡng -> Làm mờ, không tính vào số đếm hiện tại.',
      descriptionEn: 'Time gap threshold exceeded -> Dimmed, uncounted in current frame.',
      readings: [
        {
          status: 'STALE',
          zoneId: 'zone_entrance',
          zoneName: 'Lối vào chính (Zone A)',
          staleGapSeconds: 4.8,
        },
      ],
    },
    {
      id: 'fixture-6-tracked',
      nameVi: '6. Khung hình Tracked (Có định danh tạm thời)',
      nameEn: '6. Tracked Frame (Temporary anonymous IDs)',
      quality: 'VALID',
      descriptionVi: 'Mỗi người gắn track_id tạm thời trong phiên, kèm hash cấu hình tracker f6b571ba...',
      descriptionEn: 'Persons assigned session-local anonymous track IDs paired with tracker config hash.',
      isSynthetic: true,
      readings: [
        { status: 'COUNTED', count: 3, zoneId: 'zone_entrance', zoneName: 'Lối vào chính (Zone A - Tracked)' },
      ],
    },
  ];

  const zoneColors = ['#56B4E9', '#009E73', '#D55E00', '#CC79A7'];

  return (
    <div className="min-h-screen bg-abyssal text-text-primary pb-16">
      {/* Persistent Experimental Banner */}
      <Banner
        isSynthetic={true}
        locale={locale}
        onOpenSemantics={() => setShowSemantics(true)}
      />

      {/* Header Deck */}
      <header className="border-b border-contour bg-deck px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            {onBack && (
              <button
                type="button"
                onClick={onBack}
                className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface border border-transparent hover:border-contour transition-colors cursor-pointer"
                title="Quay lại"
                aria-label="Quay lại"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
            )}
            <h1 className="text-xl font-bold tracking-tight">
              CrowdSight /dev/states
            </h1>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-contour text-signal-gold border border-signal-gold/30">
              Contract Fixtures v1 Test Bench
            </span>
          </div>
          <p className="text-xs text-text-muted mt-1">
            {locale === 'vi'
              ? 'Xác minh hiển thị trực quan cho tất cả 6 trạng thái quan sát của hợp đồng v1.'
              : 'Visual fixture verification test bench for all 6 v1 observation contract states.'}
          </p>
        </div>

        <button
          type="button"
          onClick={toggleLocale}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded border border-contour bg-abyssal hover:bg-contour/60 text-xs font-medium cursor-pointer transition-colors"
        >
          <Languages className="w-4 h-4 text-signal-gold" />
          <span>{locale === 'vi' ? 'Switch to English' : 'Đổi sang Tiếng Việt'}</span>
        </button>
      </header>

      {/* Fixture Scenarios Grid */}
      <main className="max-w-7xl mx-auto px-6 py-8 space-y-10">
        {fixtures.map((fixture, idx) => (
          <section
            key={fixture.id}
            id={fixture.id}
            className="p-5 rounded-lg border border-contour bg-deck/60 space-y-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-contour/80 pb-3">
              <div>
                <h2 className="text-base font-semibold text-text-primary">
                  {locale === 'vi' ? fixture.nameVi : fixture.nameEn}
                </h2>
                <p className="text-xs text-text-muted mt-0.5">
                  {locale === 'vi' ? fixture.descriptionVi : fixture.descriptionEn}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <QualityBadge quality={fixture.quality} locale={locale} />
                {fixture.isSynthetic && (
                  <span className="px-2 py-0.5 text-[11px] font-medium bg-blue-950/60 border border-blue-500/40 text-blue-300 rounded">
                    {locale === 'vi' ? 'Mô phỏng' : 'Synthetic'}
                  </span>
                )}
              </div>
            </div>

            {/* Zone Cards Row */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {fixture.readings.map((reading, rIdx) => (
                <ZoneCard
                  key={reading.zoneId}
                  reading={reading}
                  colorHex={zoneColors[(idx + rIdx) % zoneColors.length]}
                  locale={locale}
                />
              ))}
            </div>
          </section>
        ))}
      </main>

      {/* Semantics Modal */}
      <SemanticsModal
        isOpen={showSemantics}
        onClose={() => setShowSemantics(false)}
        locale={locale}
      />
    </div>
  );
};

export const DevStatesPage: React.FC<{ onBack?: () => void }> = ({ onBack }) => {
  return (
    <LanguageWrapper>
      <DevStatesPageContent onBack={onBack} />
    </LanguageWrapper>
  );
};
