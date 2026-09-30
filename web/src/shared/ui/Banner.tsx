import React from 'react';
import { AlertTriangle, Info, Cpu } from 'lucide-react';

interface BannerProps {
  isSynthetic?: boolean;
  locale?: 'vi' | 'en';
  onOpenSemantics?: () => void;
}

export const Banner: React.FC<BannerProps> = ({
  isSynthetic = false,
  locale = 'vi',
  onOpenSemantics,
}) => {
  return (
    <div
      role="banner"
      className="w-full bg-amber-950/80 border-b border-amber-500/40 text-amber-200 px-4 py-2 flex flex-wrap items-center justify-between gap-3 text-xs"
    >
      <div className="flex items-center gap-2 font-medium">
        <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
        <span>
          {locale === 'vi'
            ? 'Thử nghiệm — chưa được duyệt cho vận hành thực tế. Cảnh báo vận hành đang tắt.'
            : 'Experimental — not approved for operational use. Operational alerts are disabled.'}
        </span>
      </div>

      <div className="flex items-center gap-3">
        {isSynthetic && (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-blue-900/60 border border-blue-400/50 text-blue-200 text-[11px] font-semibold tracking-wide uppercase">
            <Cpu className="w-3 h-3 text-blue-300" />
            <span>{locale === 'vi' ? 'Dữ liệu mô phỏng' : 'Simulated Data'}</span>
          </span>
        )}

        {onOpenSemantics && (
          <button
            type="button"
            onClick={onOpenSemantics}
            className="inline-flex items-center gap-1 text-amber-300 hover:text-white underline underline-offset-2 transition-colors cursor-pointer"
          >
            <Info className="w-3.5 h-3.5" />
            <span>{locale === 'vi' ? 'Về phép đo này' : 'About measurement'}</span>
          </button>
        )}
      </div>
    </div>
  );
};
