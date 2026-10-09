import React, { useState } from 'react';
import {
  Sliders,
  Clock,
  RotateCcw,
  Check,
} from 'lucide-react';
import type { CongestionAlertEvent, ZoneThresholdRule } from './alertUtils';
import { formatMediaTime } from '@/features/player/PlayerControls';

interface CongestionAlertsTabProps {
  alerts: CongestionAlertEvent[];
  thresholdRules: Record<string, ZoneThresholdRule>;
  zones: {
    zone_id: string;
    name: string;
    color: string;
  }[];
  onUpdateRule: (zoneId: string, updatedRule: Partial<ZoneThresholdRule>) => void;
  onResetRules: () => void;
  onSeek: (time: number) => void;
  currentTime: number;
}

export const CongestionAlertsTab: React.FC<CongestionAlertsTabProps> = ({
  alerts,
  thresholdRules,
  zones,
  onUpdateRule,
  onResetRules,
  onSeek,
  currentTime,
}) => {
  const [filterSeverity, setFilterSeverity] = useState<'ALL' | 'CRITICAL' | 'WARNING'>('ALL');
  const [showSettings, setShowSettings] = useState(false);

  const filteredAlerts = alerts.filter((a) => {
    if (filterSeverity === 'ALL') return true;
    return a.severity === filterSeverity;
  });

  const criticalCount = alerts.filter((a) => a.severity === 'CRITICAL').length;
  const warningCount = alerts.filter((a) => a.severity === 'WARNING').length;

  return (
    <div className="space-y-4 text-xs">
      {/* 1. Header Toolbar */}
      <div className="flex items-center justify-between gap-2 p-3 rounded-xl bg-brand-surface border border-brand-border">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-sm text-brand-text-primary">
              Giám Sát Quá Tải
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-brand-gold/15 text-brand-gold border border-brand-gold/30">
              {alerts.length} sự kiện
            </span>
          </div>
          <p className="text-[11px] text-brand-text-muted mt-0.5">
            Phát hiện theo ngưỡng an toàn từng khu vực
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowSettings(!showSettings)}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-medium transition-colors cursor-pointer ${
            showSettings
              ? 'bg-brand-gold/20 text-brand-gold border-brand-gold/50'
              : 'bg-brand-abyssal/60 text-brand-text-muted hover:text-brand-text-primary border-brand-border'
          }`}
          title="Tùy chỉnh ngưỡng cảnh báo"
        >
          <Sliders className="w-3.5 h-3.5" />
          <span>{showSettings ? 'Đóng cài đặt' : 'Cấu hình ngưỡng'}</span>
        </button>
      </div>

      {/* 2. Threshold Settings Drawer (if toggled open) */}
      {showSettings && (
        <div className="p-3.5 rounded-xl bg-brand-surface/90 border border-brand-gold/30 space-y-3.5 animate-fadeIn">
          <div className="flex items-center justify-between pb-2 border-b border-brand-border/60">
            <div className="font-semibold text-brand-gold flex items-center gap-1.5">
              <Sliders className="w-4 h-4" />
              <span>Thiết Lập Ngưỡng Quá Tải Từng Khu Vực</span>
            </div>
            <button
              type="button"
              onClick={onResetRules}
              className="text-[11px] text-brand-text-muted hover:text-brand-gold flex items-center gap-1 cursor-pointer transition-colors"
              title="Khôi phục mức ngưỡng mặc định tính từ đỉnh quan sát"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Đặt lại tự động</span>
            </button>
          </div>

          <div className="space-y-3">
            {zones.map((zone) => {
              const rule = thresholdRules[zone.zone_id] || {
                zoneId: zone.zone_id,
                warningThreshold: 50,
                criticalThreshold: 80,
                minDurationSeconds: 1.0,
              };

              return (
                <div
                  key={zone.zone_id}
                  className="p-2.5 rounded-lg bg-brand-abyssal/70 border border-brand-border/70 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span
                        className="w-2.5 h-2.5 rounded-full shrink-0"
                        style={{ backgroundColor: zone.color }}
                      />
                      <span className="font-semibold text-brand-text-primary">
                        {zone.name}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    {/* Warning threshold input */}
                    <div className="space-y-1">
                      <label className="text-amber-400 font-medium flex items-center justify-between">
                        <span>Cảnh báo (Vàng):</span>
                        <span className="font-mono font-bold">{rule.warningThreshold} người</span>
                      </label>
                      <input
                        type="range"
                        min="5"
                        max="250"
                        step="5"
                        value={rule.warningThreshold}
                        onChange={(e) =>
                          onUpdateRule(zone.zone_id, {
                            warningThreshold: parseInt(e.target.value, 10),
                          })
                        }
                        className="w-full h-1.5 bg-brand-border rounded-lg appearance-none cursor-pointer accent-amber-500"
                      />
                    </div>

                    {/* Critical threshold input */}
                    <div className="space-y-1">
                      <label className="text-red-400 font-medium flex items-center justify-between">
                        <span>Báo động (Đỏ):</span>
                        <span className="font-mono font-bold">{rule.criticalThreshold} người</span>
                      </label>
                      <input
                        type="range"
                        min="10"
                        max="300"
                        step="5"
                        value={rule.criticalThreshold}
                        onChange={(e) =>
                          onUpdateRule(zone.zone_id, {
                            criticalThreshold: parseInt(e.target.value, 10),
                          })
                        }
                        className="w-full h-1.5 bg-brand-border rounded-lg appearance-none cursor-pointer accent-red-500"
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 3. Filter Pills */}
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={() => setFilterSeverity('ALL')}
          className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors cursor-pointer border ${
            filterSeverity === 'ALL'
              ? 'bg-brand-gold/15 text-brand-gold border-brand-gold/40 font-bold'
              : 'bg-brand-surface text-brand-text-muted border-brand-border hover:text-brand-text-primary'
          }`}
        >
          Tất cả ({alerts.length})
        </button>
        <button
          type="button"
          onClick={() => setFilterSeverity('CRITICAL')}
          className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors cursor-pointer border ${
            filterSeverity === 'CRITICAL'
              ? 'bg-red-500/20 text-red-300 border-red-500/50 font-bold'
              : 'bg-brand-surface text-brand-text-muted border-brand-border hover:text-brand-text-primary'
          }`}
        >
          🚨 Nguy hiểm ({criticalCount})
        </button>
        <button
          type="button"
          onClick={() => setFilterSeverity('WARNING')}
          className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors cursor-pointer border ${
            filterSeverity === 'WARNING'
              ? 'bg-amber-500/20 text-amber-300 border-amber-500/50 font-bold'
              : 'bg-brand-surface text-brand-text-muted border-brand-border hover:text-brand-text-primary'
          }`}
        >
          ⚠️ Cảnh báo ({warningCount})
        </button>
      </div>

      {/* 4. Events List */}
      <div className="space-y-2">
        {filteredAlerts.length === 0 ? (
          <div className="p-6 rounded-xl bg-brand-surface border border-brand-border text-center space-y-2">
            <div className="inline-flex p-2 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              <Check className="w-4 h-4" />
            </div>
            <p className="text-brand-text-primary font-medium">
              Không có sự kiện quá tải nào trong bộ lọc này
            </p>
            <p className="text-[11px] text-brand-text-muted">
              Mật độ quan sát trong video đều nằm trong ngưỡng an toàn cho phép.
            </p>
          </div>
        ) : (
          filteredAlerts.map((alert) => {
            const isCritical = alert.severity === 'CRITICAL';
            const isActiveNow = currentTime >= alert.startTime && currentTime <= alert.endTime;

            return (
              <div
                key={alert.id}
                className={`p-3 rounded-xl border transition-all ${
                  isActiveNow
                    ? isCritical
                      ? 'bg-red-950/70 border-red-500 ring-1 ring-red-500/50 shadow-md shadow-red-950/40'
                      : 'bg-amber-950/70 border-amber-500 ring-1 ring-amber-500/50 shadow-md shadow-amber-950/40'
                    : isCritical
                      ? 'bg-brand-surface border-red-500/30 hover:border-red-500/60'
                      : 'bg-brand-surface border-amber-500/30 hover:border-amber-500/60'
                }`}
                style={{ borderLeftColor: alert.zoneColor, borderLeftWidth: '4px' }}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.2 rounded font-mono ${
                          isCritical
                            ? 'bg-red-500/20 text-red-300 border border-red-500/40'
                            : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                        }`}
                      >
                        {isCritical ? '🚨 NGUY HIỂM' : '⚠️ CẢNH BÁO'}
                      </span>
                      {isActiveNow && (
                        <span className="text-[9px] font-mono font-bold px-1 rounded bg-red-500 text-black animate-pulse">
                          ĐANG XẢY RA
                        </span>
                      )}
                      <span className="font-semibold text-brand-text-primary">
                        {alert.zoneName}
                      </span>
                    </div>

                    <div className="flex items-baseline gap-2 pt-0.5">
                      <span className="font-mono font-bold text-base text-brand-text-primary">
                        {alert.peakCount} người
                      </span>
                      <span className="text-[11px] text-brand-text-muted">
                        (Ngưỡng: {alert.threshold} • +{alert.exceedPercentage}%)
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-[11px] text-brand-text-muted pt-0.5">
                      <Clock className="w-3 h-3 text-brand-gold shrink-0" />
                      <span className="font-mono">
                        {formatMediaTime(alert.startTime)} → {formatMediaTime(alert.endTime)}
                      </span>
                      <span>({alert.duration.toFixed(1)}s)</span>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => onSeek(alert.startTime)}
                    className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-brand-abyssal/80 hover:bg-brand-gold/15 text-brand-gold border border-brand-gold/30 hover:border-brand-gold/60 transition-colors shrink-0 cursor-pointer shadow-sm"
                    title="Tua video tới thời điểm bắt đầu quá tải"
                  >
                    Tua tới
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
