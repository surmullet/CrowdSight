import React, { useState, useRef } from 'react';
import {
  Film,
  Layers,
  Cpu,
  Sliders,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  ShieldAlert,
  Sparkles,
  Info,
  UploadCloud,
  Loader2,
} from 'lucide-react';
import { Banner } from '@/shared/ui/Banner';
import { formatMediaTime } from '@/features/player/PlayerControls';

export interface MediaCatalogItem {
  id: string;
  name: string;
  duration: number;
  fps: number;
  width: number;
  height: number;
  codec: string;
  browserPlayable: boolean;
  videoSrc?: string;
}

export interface ZoneSetSummary {
  id: string;
  name: string;
  version: number;
  zoneCount: number;
}

export interface ModelProfileInfo {
  profileId: string;
  profileSha256: string;
  checkpointSha256: string;
  applicabilityStatus: string;
  operationalAlertsAllowed: boolean;
}

interface NewSessionWizardProps {
  mediaCatalog: MediaCatalogItem[];
  zoneSets: ZoneSetSummary[];
  modelProfile: ModelProfileInfo;
  onCreateZoneSet?: (selectedMediaId?: string) => void;
  onUploadMedia?: (file: File) => Promise<MediaCatalogItem>;
  onSubmit: (params: {
    mediaId: string;
    zoneSetId: string;
    zoneSetVersion: number;
    frameStride: number;
    useSynthetic: boolean;
  }) => Promise<void>;
  onCancel: () => void;
  className?: string;
}

export const NewSessionWizard: React.FC<NewSessionWizardProps> = ({
  mediaCatalog,
  zoneSets,
  modelProfile,
  onCreateZoneSet,
  onUploadMedia,
  onSubmit,
  onCancel,
  className = '',
}) => {
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3 | 4>(1);
  const [selectedMediaId, setSelectedMediaId] = useState<string>(mediaCatalog[0]?.id ?? '');
  const [selectedZoneSetId, setSelectedZoneSetId] = useState<string>(zoneSets[0]?.id ?? '');
  const [frameStride, setFrameStride] = useState<number>(5);
  const [useSynthetic, setUseSynthetic] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleProcessFile = async (file: File) => {
    if (!file) return;
    setIsUploading(true);
    setErrorMessage(null);
    try {
      if (onUploadMedia) {
        const newMedia = await onUploadMedia(file);
        setSelectedMediaId(newMedia.id);
      } else {
        const res = await fetch(`/api/v1/media/upload?filename=${encodeURIComponent(file.name)}`, {
          method: 'POST',
          body: file,
        });
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Tải tệp thất bại: ${res.statusText}`);
        }
        const data = await res.json();
        setSelectedMediaId(data.id);
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Không thể tải video lên máy chủ');
    } finally {
      setIsUploading(false);
      setIsDragging(false);
    }
  };

  const selectedMedia = mediaCatalog.find((m) => m.id === selectedMediaId);
  const selectedZoneSet = zoneSets.find((z) => z.id === selectedZoneSetId);

  const handleNext = () => {
    if (currentStep === 1 && !selectedMediaId) {
      setErrorMessage('Vui lòng chọn hoặc tải lên một video để phân tích.');
      return;
    }
    if (currentStep === 2 && !selectedZoneSetId) {
      setErrorMessage('Vui lòng chọn một tập vùng quan sát.');
      return;
    }
    setErrorMessage(null);
    setCurrentStep((prev) => (prev < 4 ? ((prev + 1) as 1 | 2 | 3 | 4) : prev));
  };

  const handleBack = () => {
    setErrorMessage(null);
    setCurrentStep((prev) => (prev > 1 ? ((prev - 1) as 1 | 2 | 3 | 4) : prev));
  };

  const handleSubmit = async () => {
    if (!selectedMediaId || !selectedZoneSetId || !selectedZoneSet) return;
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await onSubmit({
        mediaId: selectedMediaId,
        zoneSetId: selectedZoneSetId,
        zoneSetVersion: selectedZoneSet.version,
        frameStride,
        useSynthetic,
      });
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Lỗi khi khởi tạo phiên phân tích');
      setIsSubmitting(false);
    }
  };

  return (
    <div className={`flex flex-col min-h-screen bg-brand-abyssal text-brand-text-primary ${className}`}>
      {/* 1. Mandatory Top Banner */}
      <Banner />

      {/* 2. Wizard Header */}
      <header className="px-8 py-5 border-b border-brand-border bg-brand-surface/40 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-brand-text-primary">
            Khởi tạo phiên phân tích mới
          </h1>
          <p className="text-xs text-brand-text-muted mt-0.5">
            Tải video lên hoặc chọn từ danh mục máy chủ để quét mật độ đám đông
          </p>
        </div>
        <button
          type="button"
          onClick={onCancel}
          className="text-xs text-brand-text-muted hover:text-brand-text-primary"
        >
          Hủy bỏ
        </button>
      </header>

      {/* 3. Stepper Tabs */}
      <div className="px-8 py-4 border-b border-brand-border/60 bg-brand-abyssal">
        <div className="flex items-center max-w-3xl mx-auto justify-between text-xs">
          {[
            { step: 1, label: '1. Chọn video', icon: Film },
            { step: 2, label: '2. Tập vùng quan sát', icon: Layers },
            { step: 3, label: '3. Mô hình & Giới hạn', icon: Cpu },
            { step: 4, label: '4. Tùy chọn & Bắt đầu', icon: Sliders },
          ].map((item) => {
            const Icon = item.icon;
            const isActive = currentStep === item.step;
            const isCompleted = currentStep > item.step;

            return (
              <div
                key={item.step}
                className={`flex items-center gap-2 ${
                  isActive
                    ? 'text-brand-gold font-semibold'
                    : isCompleted
                    ? 'text-emerald-400'
                    : 'text-brand-text-muted'
                }`}
              >
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center border text-xs ${
                    isActive
                      ? 'border-brand-gold bg-brand-gold/10'
                      : isCompleted
                      ? 'border-emerald-500 bg-emerald-500/10'
                      : 'border-brand-border bg-brand-surface'
                  }`}
                >
                  {isCompleted ? <CheckCircle2 className="w-4 h-4" /> : <Icon className="w-3.5 h-3.5" />}
                </div>
                <span>{item.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* 4. Wizard Step Content */}
      <main className="flex-1 p-8 max-w-3xl mx-auto w-full">
        {errorMessage && (
          <div className="p-3 mb-6 bg-red-950/30 border border-red-900/50 rounded-lg text-xs text-red-300">
            {errorMessage}
          </div>
        )}

        {/* STEP 1: Select or Upload Media */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-base font-semibold text-brand-text-primary">
                Bước 1: Chọn video (Tải lên hoặc chọn từ danh mục)
              </h2>
              <p className="text-xs text-brand-text-muted mt-1">
                Tải lên video của bạn từ máy tính hoặc chọn một video có sẵn đã được quét trên máy chủ.
              </p>
            </div>

            {/* Interactive Upload Dropzone */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                const file = e.dataTransfer.files[0];
                if (file) handleProcessFile(file);
              }}
              onClick={() => fileInputRef.current?.click()}
              className={`p-6 border-2 border-dashed rounded-xl flex flex-col items-center justify-center text-center cursor-pointer transition-all ${
                isDragging
                  ? 'border-brand-gold bg-brand-gold/10'
                  : 'border-brand-border/80 bg-brand-surface/40 hover:border-brand-gold/70 hover:bg-brand-surface/70'
              }`}
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleProcessFile(file);
                }}
                accept=".mp4,.webm,.mov,.avi,.mkv,video/*"
                className="hidden"
              />
              {isUploading ? (
                <div className="flex flex-col items-center gap-2 py-2">
                  <Loader2 className="w-8 h-8 text-brand-gold animate-spin" />
                  <span className="text-xs font-medium text-brand-gold">
                    Đang tải lên và phân tích thông số video bằng OpenCV...
                  </span>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-1.5 py-1">
                  <UploadCloud className="w-8 h-8 text-brand-gold" />
                  <span className="font-semibold text-sm text-brand-text-primary">
                    Tải video mới lên từ máy tính của bạn
                  </span>
                  <span className="text-xs text-brand-text-muted">
                    Kéo thả tệp video vào đây hoặc bấm để chọn tệp (.mp4, .webm, .mov, .avi, .mkv)
                  </span>
                </div>
              )}
            </div>

            <div className="space-y-3 pt-2">
              {mediaCatalog.length === 0 ? (
                <div className="p-6 bg-brand-surface border border-brand-border rounded-lg text-center text-xs text-brand-text-muted">
                  Không tìm thấy video nào trong danh mục. Hãy quét thư mục bằng lệnh CLI: <code>crowdsight media scan</code>.
                </div>
              ) : (
                mediaCatalog.map((media) => (
                  <label
                    key={media.id}
                    className={`flex items-start gap-4 p-4 rounded-xl border cursor-pointer transition-all ${
                      selectedMediaId === media.id
                        ? 'border-brand-gold bg-brand-gold/5 shadow-sm'
                        : 'border-brand-border bg-brand-surface hover:border-brand-border/80'
                    }`}
                  >
                    <input
                      type="radio"
                      name="media"
                      value={media.id}
                      checked={selectedMediaId === media.id}
                      onChange={() => setSelectedMediaId(media.id)}
                      className="mt-1 accent-brand-gold"
                    />
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-sm text-brand-text-primary">
                          {media.name}
                        </span>
                        <span className="font-mono text-xs text-brand-gold tabular-nums">
                          {formatMediaTime(media.duration)}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-brand-text-muted mt-1">
                        <span>Độ phân giải: {media.width}×{media.height}</span>
                        <span>Tần số: {media.fps} FPS</span>
                        <span>Codec: {media.codec}</span>
                        {!media.browserPlayable && (
                          <span className="text-amber-400 text-[11px]" title="Sẽ tạo proxy H.264 tự động">
                            (cần web proxy)
                          </span>
                        )}
                      </div>
                    </div>
                  </label>
                ))
              )}
            </div>
          </div>
        )}

        {/* STEP 2: Select Zone Set */}
        {currentStep === 2 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-brand-text-primary">
                  Bước 2: Chọn tập vùng quan sát (Zone-Set)
                </h2>
                <p className="text-xs text-brand-text-muted mt-1">
                  Định nghĩa các polygon có tên để đếm số người nhìn thấy được trong từng vùng.
                </p>
              </div>
              {onCreateZoneSet && (
                <button
                  type="button"
                  onClick={() => onCreateZoneSet(selectedMediaId)}
                  className="px-3 py-1.5 bg-brand-abyssal hover:bg-brand-border border border-brand-border rounded text-xs text-brand-gold transition-colors cursor-pointer"
                >
                  + Vẽ tập vùng mới
                </button>
              )}
            </div>

            <div className="space-y-3 pt-2">
              {zoneSets.length === 0 ? (
                <div className="p-6 bg-brand-surface border border-brand-border rounded-lg text-center text-xs text-brand-text-muted">
                  Chưa có tập vùng nào. Vui lòng bấm &ldquo;Vẽ tập vùng mới&rdquo; để tạo.
                </div>
              ) : (
                zoneSets.map((zs) => (
                  <label
                    key={zs.id}
                    className={`flex items-start gap-4 p-4 rounded-xl border cursor-pointer transition-all ${
                      selectedZoneSetId === zs.id
                        ? 'border-brand-gold bg-brand-gold/5 shadow-sm'
                        : 'border-brand-border bg-brand-surface hover:border-brand-border/80'
                    }`}
                  >
                    <input
                      type="radio"
                      name="zoneSet"
                      value={zs.id}
                      checked={selectedZoneSetId === zs.id}
                      onChange={() => setSelectedZoneSetId(zs.id)}
                      className="mt-1 accent-brand-gold"
                    />
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-sm text-brand-text-primary">
                          {zs.name}
                        </span>
                        <span className="text-xs text-brand-text-muted">
                          Phiên bản v{zs.version}
                        </span>
                      </div>
                      <p className="text-xs text-brand-text-muted mt-1">
                        Bao gồm {zs.zoneCount} vùng quan sát đã được kiểm định hình học
                      </p>
                    </div>
                  </label>
                ))
              )}
            </div>
          </div>
        )}

        {/* STEP 3: Read-only Model Identity & Applicability Gate */}
        {currentStep === 3 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-semibold text-brand-text-primary">
                Bước 3: Danh tính mô hình & Tình trạng phê duyệt
              </h2>
              <p className="text-xs text-brand-text-muted mt-1">
                Kiểm tra minh bạch thông số kỹ thuật và ranh giới an toàn trước khi chạy suy luận.
              </p>
            </div>

            <div className="p-4 bg-brand-surface border border-brand-border rounded-xl space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-[11px] text-brand-text-muted">Mã hồ sơ mô hình</div>
                  <div className="font-mono text-brand-text-primary font-medium mt-0.5">
                    {modelProfile.profileId}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] text-brand-text-muted">Tình trạng phê duyệt (applicability)</div>
                  <div className="font-semibold text-amber-400 mt-0.5">
                    {modelProfile.applicabilityStatus}
                  </div>
                </div>
              </div>

              <div>
                <div className="text-[11px] text-brand-text-muted">Mã băm Profile (SHA-256)</div>
                <div className="font-mono text-[10px] text-brand-text-muted bg-brand-abyssal p-2 rounded border border-brand-border mt-1 break-all">
                  {modelProfile.profileSha256}
                </div>
              </div>

              <div>
                <div className="text-[11px] text-brand-text-muted">Mã băm Trọng số Checkpoint (SHA-256)</div>
                <div className="font-mono text-[10px] text-brand-text-muted bg-brand-abyssal p-2 rounded border border-brand-border mt-1 break-all">
                  {modelProfile.checkpointSha256}
                </div>
              </div>

              {/* Strict Disclaimer & Alerts Gate */}
              <div className="p-3 bg-red-950/20 border border-red-900/40 rounded-lg text-[11px] text-red-300 space-y-1">
                <div className="flex items-center gap-1.5 font-semibold text-red-200">
                  <ShieldAlert className="w-4 h-4 text-red-400 shrink-0" />
                  <span>Cảnh báo vận hành bị chặn hoàn toàn (Fail-closed)</span>
                </div>
                <p className="leading-relaxed">
                  Mô hình đang ở chế độ thử nghiệm phát lại. Hệ thống <strong>không tạo cảnh báo vận hành</strong>, <strong>không tính mật độ người/m²</strong>, và số đếm có thể thiếu đáng kể ở cảnh đông.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* STEP 4: Analysis Options & Confirmation */}
        {currentStep === 4 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-semibold text-brand-text-primary">
                Bước 4: Tùy chọn xử lý & Xác nhận bắt đầu
              </h2>
              <p className="text-xs text-brand-text-muted mt-1">
                Tùy chỉnh bước nhảy khung hình hoặc kích hoạt chế độ mô phỏng kiểm thử.
              </p>
            </div>

            <div className="p-5 bg-brand-surface border border-brand-border rounded-xl space-y-5 text-xs">
              {/* Frame stride option */}
              <div className="space-y-1.5">
                <label className="font-medium text-brand-text-primary flex items-center justify-between">
                  <span>Bước nhảy khung hình (frame_stride): {frameStride}</span>
                  <span className="text-[11px] text-brand-text-muted">
                    {selectedMedia ? `~${(selectedMedia.fps / frameStride).toFixed(1)} phân tích / giây` : ''}
                  </span>
                </label>
                <input
                  type="range"
                  min="1"
                  max="15"
                  value={frameStride}
                  onChange={(e) => setFrameStride(parseInt(e.target.value, 10))}
                  className="w-full accent-brand-gold bg-brand-border rounded cursor-pointer"
                />
                <p className="text-[11px] text-brand-text-muted">
                  Giá trị 1 phân tích mọi khung hình (chính xác tối đa, chậm hơn). Giá trị 5 phân tích 1 khung mỗi 5 khung hình.
                </p>
              </div>

              {/* Synthetic Mode Toggle */}
              <div className="pt-3 border-t border-brand-border/60">
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={useSynthetic}
                    onChange={(e) => setUseSynthetic(e.target.checked)}
                    className="mt-0.5 accent-purple-500 rounded"
                  />
                  <div>
                    <div className="font-medium text-brand-text-primary flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                      <span>Sử dụng bộ phát hiện mô phỏng (Synthetic Detector)</span>
                    </div>
                    <p className="text-[11px] text-brand-text-muted mt-0.5">
                      Chạy kiểm thử tất định mà không cần GPU hoặc checkpoint trọng số thực. Dữ liệu đầu ra sẽ được đánh dấu rõ là &ldquo;Dữ liệu mô phỏng&rdquo;.
                    </p>
                  </div>
                </label>
              </div>

              {/* Summary recap */}
              <div className="p-3 bg-brand-abyssal rounded-lg border border-brand-border/80 space-y-2 text-[11px]">
                <div className="font-semibold text-brand-gold flex items-center gap-1">
                  <Info className="w-3.5 h-3.5" />
                  <span>Tóm tắt phiên phân tích:</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-brand-text-muted">
                  <div>Video: <span className="text-brand-text-primary font-medium">{selectedMedia?.name}</span></div>
                  <div>Tập vùng: <span className="text-brand-text-primary font-medium">{selectedZoneSet?.name}</span></div>
                  <div>Thời lượng: <span className="text-brand-text-primary font-mono">{formatMediaTime(selectedMedia?.duration ?? 0)}</span></div>
                  <div>Chế độ: <span className="text-brand-text-primary">{useSynthetic ? 'Mô phỏng' : 'Mô hình chuẩn'}</span></div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* 5. Navigation Footer */}
      <footer className="px-8 py-4 border-t border-brand-border bg-brand-surface/40 flex items-center justify-between">
        <button
          type="button"
          onClick={handleBack}
          disabled={currentStep === 1 || isSubmitting}
          className="flex items-center gap-1.5 px-4 py-2 bg-brand-abyssal hover:bg-brand-border border border-brand-border rounded-lg text-xs font-medium text-brand-text-primary disabled:opacity-40 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Quay lại</span>
        </button>

        {currentStep < 4 ? (
          <button
            type="button"
            onClick={handleNext}
            className="flex items-center gap-1.5 px-5 py-2 bg-brand-gold hover:bg-brand-gold/90 text-brand-abyssal font-semibold rounded-lg text-xs transition-colors"
          >
            <span>Tiếp tục</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        ) : (
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="flex items-center gap-1.5 px-6 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-lg text-xs transition-colors shadow disabled:opacity-50"
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>{isSubmitting ? 'Đang khởi tạo...' : 'Bắt đầu phân tích'}</span>
          </button>
        )}
      </footer>
    </div>
  );
};
