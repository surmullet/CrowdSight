import React, { useState } from 'react';
import {
  ArrowLeft,
  Cpu,
  Copy,
  Check,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  Lock,
} from 'lucide-react';
import { Banner } from '@/shared/ui/Banner';
import { useLanguage } from '@/shared/i18n/LanguageContext';

interface ModelStatusPageProps {
  onBack?: () => void;
  modelProfileId: string;
  modelProfileSha256: string;
  checkpointSha256: string;
  applicabilityStatus: string;
  operationalAlertsAllowed: boolean;
  className?: string;
}

export const ModelStatusPage: React.FC<ModelStatusPageProps> = ({
  onBack,
  modelProfileId = 'crowd_best_local_v2',
  modelProfileSha256 = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  checkpointSha256 = '12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc',
  applicabilityStatus = 'EXPERIMENTAL_NO_APPROVAL',
  operationalAlertsAllowed = false,
  className = '',
}) => {
  const { locale } = useLanguage();
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <div className={`flex flex-col min-h-screen bg-brand-abyssal text-brand-text-primary ${className}`}>
      {/* 1. Mandatory Top Banner */}
      <Banner />

      {/* 2. Page Header */}
      <header className="px-8 py-5 border-b border-brand-border bg-brand-surface/40 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {onBack && (
            <button
              type="button"
              onClick={onBack}
              className="p-1.5 rounded-lg text-brand-text-muted hover:text-brand-text-primary hover:bg-brand-surface border border-transparent hover:border-brand-border transition-colors cursor-pointer"
              title="Quay lại"
              aria-label="Quay lại"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
          )}
          <div>
            <h1 className="text-xl font-bold tracking-tight text-brand-text-primary">
              {locale === 'vi' ? 'Mô hình & Tình trạng sử dụng' : 'Model & Applicability Status'}
            </h1>
            <p className="text-xs text-brand-text-muted mt-0.5">
              {locale === 'vi'
                ? 'Minh bạch danh tính thuật toán, mã băm mật mã và ranh giới an toàn vận hành'
                : 'Algorithmic provenance, cryptographic hashes, and operational safety boundaries'}
            </p>
          </div>
        </div>
      </header>

      {/* 3. Main Content Container */}
      <main className="flex-1 p-8 max-w-4xl mx-auto w-full space-y-6 text-xs">
        {/* Section 1: Cryptographic Model Provenance */}
        <section className="bg-brand-surface border border-brand-border rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2.5 pb-3 border-b border-brand-border">
            <Cpu className="w-5 h-5 text-brand-gold" />
            <h2 className="text-sm font-semibold text-brand-text-primary">
              Danh tính mô hình phát hiện (Provenance)
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <span className="text-[11px] text-brand-text-muted">Kiến trúc cơ sở</span>
              <div className="font-semibold text-brand-text-primary bg-brand-abyssal p-2 rounded border border-brand-border">
                YOLO11s (E01) fine-tune Plaza / VisDrone
              </div>
            </div>
            <div className="space-y-1">
              <span className="text-[11px] text-brand-text-muted">Mã hồ sơ cấu hình</span>
              <div className="font-mono text-brand-gold bg-brand-abyssal p-2 rounded border border-brand-border">
                {modelProfileId}
              </div>
            </div>
          </div>

          {/* SHA-256 Hashes with copy button */}
          <div className="space-y-3 pt-2">
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[11px] text-brand-text-muted">
                <span>Mã băm Trọng số Checkpoint (best.pt SHA-256)</span>
                <button
                  type="button"
                  onClick={() => handleCopy(checkpointSha256, 'ckpt')}
                  className="flex items-center gap-1 text-brand-gold hover:underline"
                >
                  {copiedKey === 'ckpt' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                  <span>{copiedKey === 'ckpt' ? 'Đã chép' : 'Sao chép'}</span>
                </button>
              </div>
              <div className="font-mono text-[11px] bg-brand-abyssal p-2.5 rounded border border-brand-border break-all">
                {checkpointSha256}
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between text-[11px] text-brand-text-muted">
                <span>Mã băm Hồ sơ YAML (Profile SHA-256)</span>
                <button
                  type="button"
                  onClick={() => handleCopy(modelProfileSha256, 'profile')}
                  className="flex items-center gap-1 text-brand-gold hover:underline"
                >
                  {copiedKey === 'profile' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                  <span>{copiedKey === 'profile' ? 'Đã chép' : 'Sao chép'}</span>
                </button>
              </div>
              <div className="font-mono text-[11px] bg-brand-abyssal p-2.5 rounded border border-brand-border break-all">
                {modelProfileSha256}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3 pt-2 text-brand-text-muted">
            <div className="p-2.5 bg-brand-abyssal rounded border border-brand-border">
              <div className="text-[10px]">Kích thước ảnh vào (imgsz)</div>
              <div className="font-mono font-medium text-brand-text-primary mt-0.5">1280 px</div>
            </div>
            <div className="p-2.5 bg-brand-abyssal rounded border border-brand-border">
              <div className="text-[10px]">Lớp phát hiện (class)</div>
              <div className="font-mono font-medium text-brand-text-primary mt-0.5">0 (person)</div>
            </div>
            <div className="p-2.5 bg-brand-abyssal rounded border border-brand-border">
              <div className="text-[10px]">Ngưỡng điểm thô (raw score)</div>
              <div className="font-mono font-medium text-brand-text-primary mt-0.5">0.25 (chưa hiệu chuẩn)</div>
            </div>
          </div>
        </section>

        {/* Section 2: Operating Applicability & Permitted Uses */}
        <section className="bg-brand-surface border border-brand-border rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-brand-border">
            <div className="flex items-center gap-2.5">
              <ShieldAlert className="w-5 h-5 text-amber-400" />
              <h2 className="text-sm font-semibold text-brand-text-primary">
                Tình trạng phê duyệt vận hành (Applicability)
              </h2>
            </div>
            <span className="px-2.5 py-1 rounded font-mono font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/30">
              {applicabilityStatus}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Allowed Uses */}
            <div className="p-4 bg-emerald-950/20 border border-emerald-900/40 rounded-xl space-y-2">
              <div className="flex items-center gap-1.5 font-semibold text-emerald-300">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Mục đích được phép</span>
              </div>
              <ul className="space-y-1.5 text-emerald-200/80 list-disc list-inside">
                <li>Phát lại và đối chiếu video đã ghi hình từ camera cố định.</li>
                <li>Đếm số người nhìn thấy được trong các zone vẽ trước.</li>
                <li>Quan sát xu hướng tương đối theo thời gian trong video.</li>
                <li>Heat map tương đối trong không gian ảnh (IMAGE_SPACE).</li>
              </ul>
            </div>

            {/* Prohibited Uses */}
            <div className="p-4 bg-red-950/20 border border-red-900/40 rounded-xl space-y-2">
              <div className="flex items-center gap-1.5 font-semibold text-red-300">
                <ShieldX className="w-4 h-4 text-red-400" />
                <span>Mục đích bị nghiêm cấm</span>
              </div>
              <ul className="space-y-1.5 text-red-200/80 list-disc list-inside">
                <li>Phát cảnh báo tự động điều phối hiện trường hoặc an ninh.</li>
                <li>Tuyệt đối không suy luận sức chứa, lượng người tham dự hoặc thời gian chờ.</li>
                <li>Suy luận mật độ người/m² khi chưa có hiệu chuẩn được duyệt.</li>
                <li>Áp dụng ngưỡng lọc tự ý làm sai lệch số đếm gốc.</li>
              </ul>
            </div>
          </div>
        </section>

        {/* Section 3: Operational Alerts Hard-Lock (Strictly Disabled, No Enable Button) */}
        <section className="bg-red-950/20 border border-red-900/50 rounded-xl p-6 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-red-500/20 rounded-lg text-red-400 border border-red-500/40">
                <Lock className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-red-200">
                  Cảnh báo vận hành: ĐANG TẮT HOÀN TOÀN
                </h2>
                <p className="text-[11px] text-red-300/80">
                  Cơ chế Fail-Closed bảo vệ an toàn hệ thống
                </p>
              </div>
            </div>

            <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-red-500/20 text-red-300 border border-red-500/50">
              {operationalAlertsAllowed ? 'BẬT (NGUY HIỂM)' : 'KHÓA (FAIL-CLOSED)'}
            </span>
          </div>

          <p className="text-red-200/90 leading-relaxed text-xs">
            Theo quy định an toàn của dự án CrowdSight, hệ thống cảnh báo vận hành <strong>bị khóa cứng ở mức mã nguồn</strong> khi áp dụng mô hình chưa được đánh giá độc lập tại hiện trường Việt Nam. Giao diện này <strong>không cung cấp nút bật hoặc kênh thông báo</strong> cho đến khi có văn bản phê duyệt nghiệm thu thực địa chính thức.
          </p>
        </section>
      </main>
    </div>
  );
};
