import React from 'react';
import { X, ShieldAlert, AlertCircle, FileText } from 'lucide-react';
import { useLanguage } from '@/shared/i18n/LanguageContext';

interface SemanticsModalProps {
  isOpen: boolean;
  onClose: () => void;
  locale?: 'vi' | 'en';
}

export const SemanticsModal: React.FC<SemanticsModalProps> = ({
  isOpen,
  onClose,
  locale: propLocale,
}) => {
  const { locale: contextLocale } = useLanguage();
  const locale = propLocale ?? contextLocale;
  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="semantics-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
    >
      <div className="bg-deck border border-contour rounded-lg max-w-xl w-full p-6 shadow-2xl relative text-text-primary">
        <button
          type="button"
          onClick={onClose}
          aria-label="Đóng"
          className="absolute top-4 right-4 text-text-muted hover:text-white transition-colors cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2.5 mb-4 border-b border-contour pb-3">
          <FileText className="w-5 h-5 text-signal-gold shrink-0" />
          <h2 id="semantics-title" className="text-lg font-semibold">
            {locale === 'vi' ? 'Về phép đo CrowdSight' : 'About CrowdSight Measurement'}
          </h2>
        </div>

        <div className="space-y-4 text-xs leading-relaxed max-h-[70vh] overflow-y-auto pr-1">
          <section className="p-3 rounded bg-abyssal border border-contour">
            <h3 className="font-semibold text-signal-gold mb-1">
              {locale === 'vi' ? '1. Định nghĩa số đo' : '1. Measurement Definition'}
            </h3>
            <p>
              {locale === 'vi'
                ? 'Con số hiển thị là "số người nhìn thấy được, do mô hình phát hiện, trong vùng được quan sát".'
                : 'The reported number is "visible persons detected by the model within the observed zone".'}
            </p>
          </section>

          <section className="p-3 rounded bg-abyssal border border-contour">
            <h3 className="font-semibold text-amber-400 mb-1 flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>{locale === 'vi' ? '2. Giới hạn mô hình' : '2. Model Limitations'}</span>
            </h3>
            <p>
              {locale === 'vi'
                ? 'Mô hình có thể đếm thiếu đáng kể ở các khung cảnh đám đông dày đặc. Chưa có kết quả đánh giá độc lập tại Việt Nam, sản phẩm đang ở mức thử nghiệm phát lại video (EXPERIMENTAL_NO_APPROVAL).'
                : 'The model may significantly undercount in dense crowd scenes. Independent evaluation in Vietnam is pending; currently approved strictly for experimental video replay.'}
            </p>
          </section>

          <section className="p-3 rounded bg-abyssal border border-contour">
            <h3 className="font-semibold text-red-400 mb-1 flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5" />
              <span>{locale === 'vi' ? '3. Bất biến cấm suy diễn' : '3. Prohibited Inferences'}</span>
            </h3>
            <ul className="list-disc list-inside space-y-1 text-text-muted mt-1">
              <li>
                {locale === 'vi'
                  ? 'Tuyệt đối KHÔNG coi là sức chứa, lượng người tham dự, mức an toàn hay thời gian chờ.'
                  : 'NEVER interpret as capacity, attendance, safety level, or queue wait times.'}
              </li>
              <li>
                {locale === 'vi'
                  ? 'Thiếu số liệu (UNKNOWN, STALE, NOT_FULLY_OBSERVED) KHÔNG BAO GIỜ được hiểu là "0 người".'
                  : 'Missing data (UNKNOWN, STALE, NOT_FULLY_OBSERVED) is NEVER "0 people".'}
              </li>
              <li>
                {locale === 'vi'
                  ? 'Chưa có mật độ người/m² do chưa có hiệu chuẩn hiện trường được duyệt.'
                  : 'Metric density (people/m²) is unavailable pending approved site calibration.'}
              </li>
            </ul>
          </section>
        </div>

        <div className="mt-5 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-contour hover:bg-slate-700 text-xs font-medium text-white transition-colors cursor-pointer"
          >
            {locale === 'vi' ? 'Đã hiểu' : 'Understood'}
          </button>
        </div>
      </div>
    </div>
  );
};
