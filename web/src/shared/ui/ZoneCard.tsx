import type { ZoneReading } from '@/shared/types/domain';
import { AlertTriangle, EyeOff, Clock, ShieldCheck, ShieldAlert } from 'lucide-react';
import { useLanguage } from '@/shared/i18n/LanguageContext';
import type { ZoneThresholdRule } from '@/features/alerts/alertUtils';

interface ZoneCardProps {
  reading: ZoneReading;
  colorHex?: string;
  thresholdRule?: ZoneThresholdRule;
  locale?: 'vi' | 'en';
  className?: string;
}

export const ZoneCard: React.FC<ZoneCardProps> = ({
  reading,
  colorHex = '#56B4E9',
  thresholdRule,
  locale: propLocale,
  className = '',
}) => {
  const { locale: contextLocale } = useLanguage();
  const locale = propLocale ?? contextLocale;

  const isCritical =
    reading.status === 'COUNTED' &&
    thresholdRule !== undefined &&
    reading.count >= thresholdRule.criticalThreshold;

  const isWarning =
    reading.status === 'COUNTED' &&
    thresholdRule !== undefined &&
    !isCritical &&
    reading.count >= thresholdRule.warningThreshold;

  return (
    <div
      className={`relative p-4 rounded-md border bg-deck overflow-hidden flex flex-col justify-between transition-colors ${
        isCritical
          ? 'border-red-500/80 bg-red-950/20 shadow-md shadow-red-950/30'
          : isWarning
            ? 'border-amber-500/80 bg-amber-950/20 shadow-md shadow-amber-950/30'
            : 'border-contour'
      } ${className}`}
      style={{ borderLeftColor: colorHex, borderLeftWidth: '4px' }}
    >
      {/* Zone Header */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <span
            className="w-2.5 h-2.5 rounded-full shrink-0"
            style={{ backgroundColor: colorHex }}
          />
          <span className="font-semibold text-sm text-text-primary">
            {reading.zoneName}
          </span>
        </div>

        {/* Real-time Overcrowding Badge */}
        {isCritical && (
          <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-500/20 text-red-300 border border-red-500/40 font-mono animate-pulse">
            <ShieldAlert className="w-3 h-3" />
            <span>QUÁ TẢI (≥{thresholdRule?.criticalThreshold})</span>
          </span>
        )}
        {isWarning && (
          <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 font-mono">
            <AlertTriangle className="w-3 h-3" />
            <span>CẢNH BÁO (≥{thresholdRule?.warningThreshold})</span>
          </span>
        )}
      </div>

      {/* Main Zone State Body */}
      {reading.status === 'COUNTED' && reading.count > 0 && (
        <div className="mt-1">
          <div className="flex items-baseline gap-2">
            <span className={`text-3xl font-bold tabular-nums tracking-tight ${
              isCritical ? 'text-red-400' : isWarning ? 'text-amber-400' : 'text-text-primary'
            }`}>
              {reading.count}
            </span>
            <span className="text-xs text-text-muted">
              {locale === 'vi' ? 'người nhìn thấy' : 'visible people'}
            </span>
          </div>
          {reading.isPartialObservation && (
            <div className="mt-2 inline-flex items-center gap-1 text-[11px] text-amber-400 bg-amber-950/40 px-2 py-0.5 rounded border border-amber-500/30">
              <AlertTriangle className="w-3 h-3 shrink-0" />
              <span>{locale === 'vi' ? 'Quan sát một phần' : 'Partial observation'}</span>
            </div>
          )}
        </div>
      )}

      {reading.status === 'COUNTED' && reading.count === 0 && (
        <div className="mt-2 p-2.5 rounded bg-teal-950/30 border border-teal-500/40 flex items-start gap-2">
          <ShieldCheck className="w-4 h-4 text-teal-400 shrink-0 mt-0.5" />
          <div className="text-xs text-teal-200">
            <span className="font-bold text-sm tabular-nums mr-1">0</span>
            <span>
              {locale === 'vi'
                ? 'người được nhìn thấy — vùng đã quan sát đầy đủ'
                : 'people observed — zone fully observed'}
            </span>
          </div>
        </div>
      )}

      {reading.status === 'NOT_FULLY_OBSERVED' && (
        <div className="mt-2 p-3 rounded pattern-diagonal-hatching border border-amber-500/30 bg-amber-950/20">
          <div className="flex items-center gap-1.5 text-amber-300 text-xs font-medium">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              {locale === 'vi'
                ? 'Chưa quan sát đầy đủ vùng này'
                : 'Zone not fully observed in this frame'}
            </span>
          </div>
          <p className="text-[11px] text-text-muted mt-1">
            {locale === 'vi'
              ? 'Không có số liệu đếm — camera bị che khuất hoặc khung hình suy giảm'
              : 'Count unavailable — obscured camera or degraded frame'}
          </p>
        </div>
      )}

      {reading.status === 'UNKNOWN' && (
        <div className="mt-2 p-3 rounded pattern-dot-stipple border border-slate-600/40 bg-slate-900/50">
          <div className="flex items-center gap-1.5 text-slate-300 text-xs font-medium">
            <EyeOff className="w-4 h-4 text-slate-400 shrink-0" />
            <span>
              {locale === 'vi'
                ? 'Không có số liệu đáng tin cậy ở khung hình này'
                : 'No reliable observation for this frame'}
            </span>
          </div>
          {reading.reasonCode && (
            <p className="text-[11px] text-slate-400 mt-1 font-mono">
              [{reading.reasonCode}]
            </p>
          )}
        </div>
      )}

      {reading.status === 'STALE' && (
        <div className="mt-2 p-2.5 rounded border border-purple-500/30 bg-purple-950/20 opacity-70">
          <div className="flex items-center gap-1.5 text-purple-300 text-xs">
            <Clock className="w-4 h-4 text-purple-400 shrink-0" />
            <span>
              {locale === 'vi'
                ? `Số liệu đã cũ (cách ${reading.staleGapSeconds.toFixed(1)}s)`
                : `Data is stale (${reading.staleGapSeconds.toFixed(1)}s ago)`}
            </span>
          </div>
          <p className="text-[11px] text-text-muted mt-0.5">
            {locale === 'vi' ? 'Không thể dùng để đếm hiện tại' : 'Cannot be used for current count'}
          </p>
        </div>
      )}
    </div>
  );
};
