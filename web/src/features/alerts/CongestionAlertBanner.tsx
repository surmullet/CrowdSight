import React from 'react';
import { AlertTriangle, ShieldAlert, ArrowRight, X } from 'lucide-react';
import type { CongestionAlertEvent } from './alertUtils';
import { formatMediaTime } from '@/features/player/PlayerControls';

interface CongestionAlertBannerProps {
  alerts: CongestionAlertEvent[];
  onSeek?: (time: number) => void;
  onOpenAlertsTab?: () => void;
  onDismiss?: () => void;
  className?: string;
}

export const CongestionAlertBanner: React.FC<CongestionAlertBannerProps> = ({
  alerts,
  onSeek,
  onOpenAlertsTab,
  onDismiss,
  className = '',
}) => {
  if (alerts.length === 0) return null;

  // Prioritize critical alert over warning if multiple are active
  const topAlert = alerts.find((a) => a.severity === 'CRITICAL') || alerts[0]!;
  const isCritical = topAlert.severity === 'CRITICAL';
  const otherCount = alerts.length - 1;

  return (
    <div
      role="alert"
      aria-live="assertive"
      className={`relative px-4 py-2.5 rounded-xl border flex flex-wrap items-center justify-between gap-3 shadow-2xl backdrop-blur-md transition-all duration-300 animate-fadeIn ${
        isCritical
          ? 'bg-red-950/90 border-red-500/80 text-red-100 shadow-red-950/60 ring-1 ring-red-500/30'
          : 'bg-amber-950/90 border-amber-500/80 text-amber-100 shadow-amber-950/60 ring-1 ring-amber-500/30'
      } ${className}`}
    >
      <div className="flex items-center gap-3">
        <div
          className={`p-1.5 rounded-lg shrink-0 ${
            isCritical
              ? 'bg-red-500/20 text-red-400 border border-red-500/40 animate-pulse'
              : 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
          }`}
        >
          {isCritical ? (
            <ShieldAlert className="w-5 h-5 text-red-400" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-amber-400" />
          )}
        </div>

        <div>
          <div className="flex items-center gap-2">
            <span
              className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded font-mono ${
                isCritical
                  ? 'bg-red-500 text-black'
                  : 'bg-amber-500 text-black'
              }`}
            >
              {isCritical ? '🚨 Báo Động Quá Tải Đỏ' : '⚠️ Cảnh Báo Ngưỡng Vàng'}
            </span>
            {otherCount > 0 && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/20 text-white font-semibold">
                +{otherCount} khu vực khác
              </span>
            )}
            <span className="text-xs font-bold font-mono">
              {formatMediaTime(topAlert.startTime)}
            </span>
          </div>

          <p className="text-xs mt-0.5 font-medium">
            Khu vực <strong className="underline decoration-current underline-offset-2">{topAlert.zoneName}</strong>{' '}
            ghi nhận{' '}
            <strong className="font-mono text-sm">
              {topAlert.peakCount} người
            </strong>{' '}
            (Vượt ngưỡng định mức {topAlert.threshold} người, +{topAlert.exceedPercentage}%).
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {onSeek && (
          <button
            type="button"
            onClick={() => onSeek(topAlert.startTime)}
            className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-black/40 hover:bg-black/60 border border-white/20 transition-colors cursor-pointer text-white"
          >
            Tua tới mốc này
          </button>
        )}

        {onOpenAlertsTab && (
          <button
            type="button"
            onClick={onOpenAlertsTab}
            className={`flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer shadow-sm ${
              isCritical
                ? 'bg-red-500 hover:bg-red-400 text-black'
                : 'bg-amber-500 hover:bg-amber-400 text-black'
            }`}
          >
            <span>Chi tiết cảnh báo</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        )}

        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            className="p-1 rounded-lg text-white/70 hover:text-white hover:bg-white/20 transition-colors cursor-pointer"
            title="Đóng thông báo này"
            aria-label="Đóng thông báo"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
};
