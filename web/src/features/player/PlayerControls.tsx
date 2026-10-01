import React from 'react';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Box,
  Layers,
  Flame,
  HelpCircle,
} from 'lucide-react';
import { usePlaybackStore } from '@/shared/state/playbackStore';

interface PlayerControlsProps {
  onStepFrame?: (deltaSeconds: number) => void;
  className?: string;
}

export function formatMediaTime(seconds: number): string {
  if (isNaN(seconds) || seconds < 0) return '00:00.00';
  const totalHundredths = Math.round(seconds * 100);
  const hundredths = totalHundredths % 100;
  const totalSeconds = Math.floor(totalHundredths / 100);
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${hundredths.toString().padStart(2, '0')}`;
}

export const PlayerControls: React.FC<PlayerControlsProps> = ({
  onStepFrame,
  className = '',
}) => {
  const {
    currentTime,
    duration,
    isPlaying,
    playbackRate,
    showBoxes,
    showZones,
    showHeatmap,
    heatmapOpacity,
    setIsPlaying,
    setCurrentTime,
    setPlaybackRate,
    toggleBoxes,
    toggleZones,
    toggleHeatmap,
    setHeatmapOpacity,
  } = usePlaybackStore();

  const [showHelp, setShowHelp] = React.useState(false);

  const handleStep = (delta: number) => {
    setIsPlaying(false);
    const newTime = Math.max(0, Math.min(duration || 1000, currentTime + delta));
    setCurrentTime(newTime);
    if (onStepFrame) {
      onStepFrame(delta);
    }
  };

  const rates = [0.5, 1.0, 2.0];
  const nextRateIndex = (rates.indexOf(playbackRate) + 1) % rates.length;
  const cycleRate = () => {
    setPlaybackRate(rates[nextRateIndex] ?? 1.0);
  };

  return (
    <div
      className={`flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 bg-brand-surface border border-brand-border rounded-lg text-brand-text-primary text-sm select-none ${className}`}
      role="toolbar"
      aria-label="Điều khiển phát video và các lớp chú thích"
    >
      {/* Left: Playback controls & step */}
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={() => setIsPlaying(!isPlaying)}
          className="p-2 rounded hover:bg-brand-border text-brand-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-brand-gold"
          title={isPlaying ? 'Tạm dừng (Phím cách)' : 'Phát (Phím cách)'}
          aria-label={isPlaying ? 'Tạm dừng' : 'Phát'}
        >
          {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 fill-current" />}
        </button>

        <button
          type="button"
          onClick={() => handleStep(-0.04)}
          className="p-1.5 rounded hover:bg-brand-border text-brand-text-muted hover:text-brand-text-primary transition-colors"
          title="Lùi 1 khung hình (←)"
          aria-label="Lùi một khung hình"
        >
          <SkipBack className="w-4 h-4" />
        </button>

        <button
          type="button"
          onClick={() => handleStep(0.04)}
          className="p-1.5 rounded hover:bg-brand-border text-brand-text-muted hover:text-brand-text-primary transition-colors"
          title="Tiến 1 khung hình (→)"
          aria-label="Tiến một khung hình"
        >
          <SkipForward className="w-4 h-4" />
        </button>

        {/* Playback speed toggle */}
        <button
          type="button"
          onClick={cycleRate}
          className="px-2 py-1 ml-1 rounded font-mono text-xs text-brand-text-muted hover:text-brand-text-primary bg-brand-abyssal/60 border border-brand-border hover:border-brand-gold/50 transition-colors"
          title="Thay đổi tốc độ phát"
          aria-label={`Tốc độ phát hiện tại: ${playbackRate}x`}
        >
          {playbackRate}x
        </button>

        {/* Media timestamp display (Strictly media_time_s, not real-world clock time) */}
        <div className="flex items-baseline gap-1 ml-2 font-mono text-xs tabular-nums">
          <span className="text-brand-gold font-medium" aria-label="Thời gian trôi qua trong video">
            {formatMediaTime(currentTime)}
          </span>
          <span className="text-brand-text-muted">/</span>
          <span className="text-brand-text-muted" aria-label="Tổng thời lượng video">
            {formatMediaTime(duration)}
          </span>
          <span className="text-[10px] text-brand-text-muted ml-0.5" title="Thời gian trôi qua trong bản ghi (media_time_s)">
            (media)
          </span>
        </div>
      </div>

      {/* Right: Layer Toggles and Shortcuts Help */}
      <div className="flex items-center gap-2">
        {/* Person Boxes Toggle */}
        <button
          type="button"
          onClick={toggleBoxes}
          className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs transition-colors border ${
            showBoxes
              ? 'bg-brand-gold/15 text-brand-gold border-brand-gold/40'
              : 'bg-brand-abyssal/40 text-brand-text-muted border-brand-border hover:text-brand-text-primary'
          }`}
          aria-pressed={showBoxes}
          title="Bật/tắt khung người nhìn thấy được (Phím B)"
        >
          <Box className="w-3.5 h-3.5" />
          <span>Boxes</span>
        </button>

        {/* Zone Polygons Toggle */}
        <button
          type="button"
          onClick={toggleZones}
          className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs transition-colors border ${
            showZones
              ? 'bg-blue-500/15 text-blue-400 border-blue-500/40'
              : 'bg-brand-abyssal/40 text-brand-text-muted border-brand-border hover:text-brand-text-primary'
          }`}
          aria-pressed={showZones}
          title="Bật/tắt ranh giới các zone (Phím Z)"
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Zones</span>
        </button>

        {/* Heatmap Toggle & Opacity Slider */}
        <div className="flex items-center gap-1.5 pl-1 border-l border-brand-border/60">
          <button
            type="button"
            onClick={toggleHeatmap}
            className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs transition-colors border ${
              showHeatmap
                ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/40'
                : 'bg-brand-abyssal/40 text-brand-text-muted border-brand-border hover:text-brand-text-primary'
            }`}
            aria-pressed={showHeatmap}
            title="Bật/tắt heat map tương đối (Phím H)"
          >
            <Flame className="w-3.5 h-3.5" />
            <span>Heat map</span>
          </button>

          {showHeatmap && (
            <div className="flex items-center gap-1 text-[11px] text-brand-text-muted" title="Độ mờ heat map">
              <input
                type="range"
                min="0.1"
                max="1"
                step="0.05"
                value={heatmapOpacity}
                onChange={(e) => setHeatmapOpacity(parseFloat(e.target.value))}
                className="w-16 h-1 accent-emerald-500 bg-brand-border rounded cursor-pointer"
                aria-label="Độ mờ của lớp heat map"
              />
              <span className="font-mono tabular-nums text-[10px] w-6">
                {Math.round(heatmapOpacity * 100)}%
              </span>
            </div>
          )}
        </div>

        {/* Keyboard shortcut help button */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowHelp(!showHelp)}
            className="p-1 rounded text-brand-text-muted hover:text-brand-text-primary hover:bg-brand-border transition-colors"
            title="Trợ giúp phím tắt"
            aria-label="Xem trợ giúp phím tắt"
          >
            <HelpCircle className="w-4 h-4" />
          </button>

          {showHelp && (
            <div className="absolute right-0 bottom-full mb-2 w-64 p-3 bg-brand-abyssal border border-brand-border rounded-lg shadow-xl text-xs z-50">
              <div className="flex items-center justify-between pb-1.5 mb-2 border-b border-brand-border">
                <span className="font-medium text-brand-text-primary">Phím tắt bàn phím</span>
                <button
                  type="button"
                  onClick={() => setShowHelp(false)}
                  className="text-brand-text-muted hover:text-brand-text-primary text-[11px]"
                >
                  ✕
                </button>
              </div>
              <ul className="space-y-1.5 text-brand-text-muted">
                <li className="flex justify-between">
                  <span>Phát / Tạm dừng</span>
                  <kbd className="px-1 bg-brand-surface border border-brand-border rounded font-mono text-[10px]">Space</kbd>
                </li>
                <li className="flex justify-between">
                  <span>Lùi / Tiến 1 khung hình</span>
                  <kbd className="px-1 bg-brand-surface border border-brand-border rounded font-mono text-[10px]">← / →</kbd>
                </li>
                <li className="flex justify-between">
                  <span>Bật/tắt Box người</span>
                  <kbd className="px-1 bg-brand-surface border border-brand-border rounded font-mono text-[10px]">B</kbd>
                </li>
                <li className="flex justify-between">
                  <span>Bật/tắt ranh giới Zone</span>
                  <kbd className="px-1 bg-brand-surface border border-brand-border rounded font-mono text-[10px]">Z</kbd>
                </li>
                <li className="flex justify-between">
                  <span>Bật/tắt Heat map</span>
                  <kbd className="px-1 bg-brand-surface border border-brand-border rounded font-mono text-[10px]">H</kbd>
                </li>
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
