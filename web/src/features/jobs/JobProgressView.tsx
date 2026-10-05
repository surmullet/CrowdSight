import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  Loader2,
  XCircle,
  AlertTriangle,
  Play,
  Gauge,
  Clock,
  Sparkles,
  ArrowRight,
} from 'lucide-react';
import { Banner } from '@/shared/ui/Banner';
import { formatMediaTime } from '@/features/player/PlayerControls';

export interface JobProgressData {
  sessionId: string;
  mediaName: string;
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLING' | 'CANCELLED';
  progress: number; // 0 to 1
  currentFrame: number;
  totalFrames: number;
  fps: number;
  etaSeconds: number;
  qualityCounts: {
    valid: number;
    partial: number;
    unknown: number;
    stale: number;
  };
  errorCode?: string | null;
  userActionHint?: string | null;
  synthetic?: boolean;
}

interface JobProgressViewProps {
  sessionId: string;
  initialData?: JobProgressData;
  onComplete: () => void;
  onOpenPartialResults: () => void;
  onBackToLibrary: () => void;
  className?: string;
}

export const JobProgressView: React.FC<JobProgressViewProps> = ({
  sessionId,
  initialData,
  onComplete,
  onOpenPartialResults,
  onBackToLibrary,
  className = '',
}) => {
  const [job, setJob] = useState<JobProgressData>(
    initialData ?? {
      sessionId,
      mediaName: 'Đang tải thông tin video...',
      status: 'QUEUED',
      progress: 0,
      currentFrame: 0,
      totalFrames: 100,
      fps: 0,
      etaSeconds: 0,
      qualityCounts: { valid: 0, partial: 0, unknown: 0, stale: 0 },
    }
  );

  const [isCancelling, setIsCancelling] = useState(false);
  const sseRef = useRef<EventSource | null>(null);

  // Poll fallback function
  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`/api/v1/sessions/${sessionId}`);
      if (res.ok) {
        const data = await res.json();
        setJob((prev) => ({
          ...prev,
          status: data.status,
          progress: data.progress ?? 0,
          currentFrame: data.current_frame ?? 0,
          totalFrames: data.total_frames ?? 100,
          errorCode: data.error_code,
          userActionHint: data.user_action_hint,
          synthetic: data.synthetic,
        }));
        if (data.status === 'COMPLETED') {
          onComplete();
        }
      }
    } catch {
      // Ignore polling errors
    }
  }, [sessionId, onComplete]);

  // Connect to SSE stream
  useEffect(() => {
    fetchStatus();

    const sse = new EventSource(`/api/v1/sessions/${sessionId}/events`);
    sseRef.current = sse;

    const handleProgressData = (payload: any) => {
      setJob((prev) => ({
        ...prev,
        status: payload.status,
        progress: payload.progress ?? prev.progress,
        currentFrame: payload.processed_frames ?? payload.currentFrame ?? prev.currentFrame,
        totalFrames: payload.total_frames ?? payload.totalFrames ?? prev.totalFrames,
        errorCode: payload.error_code ?? payload.errorCode,
        userActionHint: payload.user_action_hint ?? payload.userActionHint,
        synthetic: payload.synthetic ?? prev.synthetic,
      }));

      if (payload.status === 'COMPLETED') {
        sse.close();
        onComplete();
      } else if (
        payload.status === 'FAILED' ||
        payload.status === 'CANCELLED' ||
        payload.status === 'PARTIAL_CANCELLED'
      ) {
        sse.close();
      }
    };

    sse.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        handleProgressData(payload);
      } catch {
        // SSE parse error
      }
    };

    if (typeof sse.addEventListener === 'function') {
      sse.addEventListener('progress', (event: any) => {
        try {
          const payload = JSON.parse(event.data);
          handleProgressData(payload);
        } catch {
          // SSE parse error
        }
      });

      sse.addEventListener('done', (event: any) => {
        try {
          const payload = JSON.parse(event.data);
          handleProgressData(payload);
        } catch {
          // SSE parse error
        }
      });
    }

    let pollInterval: ReturnType<typeof setInterval> | null = null;

    sse.onerror = () => {
      sse.close();
      if (!pollInterval) {
        pollInterval = setInterval(async () => {
          try {
            const res = await fetch(`/api/v1/sessions/${sessionId}`);
            if (res.ok) {
              const data = await res.json();
              handleProgressData(data);
              if (
                data.status === 'COMPLETED' ||
                data.status === 'FAILED' ||
                data.status === 'CANCELLED' ||
                data.status === 'PARTIAL_CANCELLED'
              ) {
                if (pollInterval) clearInterval(pollInterval);
              }
            }
          } catch {
            // Polling network retry
          }
        }, 1000);
      }
    };

    return () => {
      sse.close();
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [sessionId, onComplete]);

  const handleCancel = async () => {
    setIsCancelling(true);
    try {
      await fetch(`/api/v1/sessions/${sessionId}/cancel`, { method: 'POST' });
      setJob((prev) => ({ ...prev, status: 'CANCELLING' }));
    } catch {
      // Cancel request error
    } finally {
      setIsCancelling(false);
    }
  };

  const progressPct = Math.round(job.progress * 100);

  return (
    <div className={`flex flex-col min-h-screen bg-brand-abyssal text-brand-text-primary ${className}`}>
      {/* 1. Mandatory Top Banner */}
      <Banner isSynthetic={job.synthetic} />

      {/* 2. Top Header */}
      <header className="px-8 py-5 border-b border-brand-border bg-brand-surface/40 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-brand-text-primary">
              Tiến độ phân tích video
            </h1>
            {job.synthetic && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] bg-purple-500/10 text-purple-300 border border-purple-500/30">
                <Sparkles className="w-2.5 h-2.5" />
                Mô phỏng
              </span>
            )}
          </div>
          <p className="text-xs text-brand-text-muted mt-0.5 font-mono">
            Mã phiên: {sessionId} • Nguồn: {job.mediaName}
          </p>
        </div>

        <button
          type="button"
          onClick={onBackToLibrary}
          className="text-xs text-brand-text-muted hover:text-brand-text-primary"
        >
          Trở về thư viện
        </button>
      </header>

      {/* 3. Main Progress Console */}
      <main className="flex-1 p-8 max-w-2xl mx-auto w-full flex flex-col justify-center">
        <div className="bg-brand-surface border border-brand-border rounded-2xl p-8 shadow-xl space-y-6">
          {/* Status Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {job.status === 'RUNNING' || job.status === 'QUEUED' || job.status === 'CANCELLING' ? (
                <div className="p-2.5 rounded-xl bg-brand-gold/10 text-brand-gold border border-brand-gold/30">
                  <Loader2 className="w-6 h-6 animate-spin" />
                </div>
              ) : job.status === 'FAILED' ? (
                <div className="p-2.5 rounded-xl bg-red-500/10 text-red-400 border border-red-500/30">
                  <AlertTriangle className="w-6 h-6" />
                </div>
              ) : (
                <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/30">
                  <XCircle className="w-6 h-6" />
                </div>
              )}

              <div>
                <h2 className="text-base font-bold text-brand-text-primary">
                  {job.status === 'QUEUED' && 'Đang xếp hàng chờ xử lý...'}
                  {job.status === 'RUNNING' && 'Đang giải mã và phát hiện đối tượng...'}
                  {job.status === 'CANCELLING' && 'Đang dừng tiến trình hợp tác...'}
                  {job.status === 'CANCELLED' && 'Phiên phân tích đã dừng'}
                  {job.status === 'FAILED' && 'Xử lý thất bại'}
                </h2>
                <p className="text-xs text-brand-text-muted mt-0.5">
                  Khung {job.currentFrame} / {job.totalFrames} ({progressPct}%)
                </p>
              </div>
            </div>

            <span className="font-mono text-xl font-bold text-brand-gold tabular-nums">
              {progressPct}%
            </span>
          </div>

          {/* Large Progress Bar */}
          <div className="space-y-1.5">
            <div className="w-full h-3 bg-brand-abyssal rounded-full overflow-hidden border border-brand-border flex">
              <div
                style={{ width: `${progressPct}%` }}
                className="bg-brand-gold transition-all duration-300 rounded-full"
              />
            </div>
            <div className="flex items-center justify-between text-[11px] text-brand-text-muted">
              <span className="flex items-center gap-1 font-mono">
                <Gauge className="w-3.5 h-3.5" />
                {job.fps.toFixed(1)} FPS xử lý
              </span>
              <span className="flex items-center gap-1 font-mono">
                <Clock className="w-3.5 h-3.5" />
                ETA: {formatMediaTime(job.etaSeconds)}
              </span>
            </div>
          </div>

          {/* Real-time Live Quality Tally */}
          <div className="space-y-2 pt-2">
            <span className="text-[11px] font-medium text-brand-text-muted uppercase tracking-wider">
              Bộ đếm chất lượng khung hình trực tiếp
            </span>
            <div className="grid grid-cols-4 gap-2 text-center text-xs">
              <div className="p-2.5 bg-brand-abyssal/60 rounded-lg border border-brand-border">
                <div className="text-[10px] text-emerald-400 font-medium">VALID</div>
                <div className="font-mono text-sm font-bold text-brand-text-primary tabular-nums mt-0.5">
                  {job.qualityCounts.valid}
                </div>
              </div>
              <div className="p-2.5 bg-brand-abyssal/60 rounded-lg border border-brand-border">
                <div className="text-[10px] text-amber-400 font-medium">PARTIAL</div>
                <div className="font-mono text-sm font-bold text-brand-text-primary tabular-nums mt-0.5">
                  {job.qualityCounts.partial}
                </div>
              </div>
              <div className="p-2.5 bg-brand-abyssal/60 rounded-lg border border-brand-border">
                <div className="text-[10px] text-slate-400 font-medium">UNKNOWN</div>
                <div className="font-mono text-sm font-bold text-brand-text-primary tabular-nums mt-0.5">
                  {job.qualityCounts.unknown}
                </div>
              </div>
              <div className="p-2.5 bg-brand-abyssal/60 rounded-lg border border-brand-border">
                <div className="text-[10px] text-red-400 font-medium">STALE</div>
                <div className="font-mono text-sm font-bold text-brand-text-primary tabular-nums mt-0.5">
                  {job.qualityCounts.stale}
                </div>
              </div>
            </div>
          </div>

          {/* Actionable Error Display (RFC 9457 error_code + user_action_hint) */}
          {job.status === 'FAILED' && (
            <div className="p-4 bg-red-950/30 border border-red-900/60 rounded-xl space-y-2 text-xs text-red-200">
              <div className="font-semibold flex items-center gap-1.5 text-red-300">
                <AlertTriangle className="w-4 h-4 text-red-400" />
                <span>Mã lỗi: {job.errorCode ?? 'UNKNOWN_ERROR'}</span>
              </div>
              <p className="leading-relaxed">
                {job.userActionHint ??
                  'Tiến trình phân tích gặp sự cố bất ngờ. Vui lòng kiểm tra lại cấu hình video hoặc checkpoint mô hình.'}
              </p>
            </div>
          )}

          {/* Cooperative Cancellation & Recovery Actions */}
          <div className="pt-4 border-t border-brand-border/60 flex items-center justify-between">
            {job.status === 'RUNNING' || job.status === 'QUEUED' ? (
              <button
                type="button"
                onClick={handleCancel}
                disabled={isCancelling}
                className="px-4 py-2 bg-brand-abyssal hover:bg-red-950/40 border border-brand-border hover:border-red-900 text-xs font-medium text-red-300 rounded-lg transition-colors flex items-center gap-1.5"
              >
                <XCircle className="w-3.5 h-3.5" />
                <span>{isCancelling ? 'Đang gửi lệnh dừng...' : 'Hủy phân tích'}</span>
              </button>
            ) : job.status === 'CANCELLED' ? (
              <button
                type="button"
                onClick={onOpenPartialResults}
                className="px-4 py-2 bg-brand-gold hover:bg-brand-gold/90 text-brand-abyssal text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 shadow"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Mở kết quả một phần ({job.currentFrame} khung)</span>
              </button>
            ) : job.status === 'FAILED' ? (
              <button
                type="button"
                onClick={onBackToLibrary}
                className="px-4 py-2 bg-brand-abyssal hover:bg-brand-border border border-brand-border text-xs text-brand-text-primary rounded-lg transition-colors"
              >
                Quay lại thư viện
              </button>
            ) : null}

            {job.status === 'COMPLETED' && (
              <button
                type="button"
                onClick={onComplete}
                className="ml-auto px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 shadow"
              >
                <span>Xem kết quả phân tích</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};
