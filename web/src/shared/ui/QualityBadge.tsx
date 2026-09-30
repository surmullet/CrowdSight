import React from 'react';
import type { FrameQuality } from '@/shared/types/domain';
import { CheckCircle2, AlertCircle, HelpCircle, Clock } from 'lucide-react';

interface QualityBadgeProps {
  quality: FrameQuality;
  locale?: 'vi' | 'en';
  className?: string;
}

export const QualityBadge: React.FC<QualityBadgeProps> = ({
  quality,
  locale = 'vi',
  className = '',
}) => {
  const configs = {
    VALID: {
      labelVi: 'Đầy đủ (VALID)',
      labelEn: 'Valid (Fully Observed)',
      bg: 'bg-teal-950/40 border-teal-500/40 text-teal-300',
      icon: <CheckCircle2 className="w-3.5 h-3.5 text-teal-400 shrink-0" />,
      pattern: '',
    },
    PARTIAL: {
      labelVi: 'Một phần (PARTIAL)',
      labelEn: 'Partial Observation',
      bg: 'bg-amber-950/40 border-amber-500/40 text-amber-300 pattern-diagonal-hatching',
      icon: <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />,
      pattern: '',
    },
    UNKNOWN: {
      labelVi: 'Không xác định (UNKNOWN)',
      labelEn: 'Unknown / Unusable',
      bg: 'bg-slate-900/60 border-slate-600/40 text-slate-300 pattern-dot-stipple',
      icon: <HelpCircle className="w-3.5 h-3.5 text-slate-400 shrink-0" />,
      pattern: '',
    },
    STALE: {
      labelVi: 'Đã cũ (STALE)',
      labelEn: 'Stale Evidence',
      bg: 'bg-purple-950/40 border-purple-500/40 text-purple-300 opacity-70',
      icon: <Clock className="w-3.5 h-3.5 text-purple-400 shrink-0" />,
      pattern: '',
    },
  };

  const cfg = configs[quality];
  const label = locale === 'vi' ? cfg.labelVi : cfg.labelEn;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium border ${cfg.bg} ${className}`}
      title={label}
    >
      {cfg.icon}
      <span>{label}</span>
    </span>
  );
};
