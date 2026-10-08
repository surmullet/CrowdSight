import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Clock,
  ShieldAlert,
  Copy,
  Check,
  FileSpreadsheet,
  FileCode,
  Plus,
  Trash2,
  Info,
  Layers,
  RotateCcw,
} from 'lucide-react';
import type { CrowdFrameObservation, ZoneReading } from '@/shared/types/domain';
import { Banner } from '@/shared/ui/Banner';
import { QualityBadge } from '@/shared/ui/QualityBadge';
import { ZoneCard } from '@/shared/ui/ZoneCard';
import { SemanticsModal } from '@/shared/ui/SemanticsModal';
import { AnnotatedPlayer } from '@/features/player/AnnotatedPlayer';
import { PlayerControls, formatMediaTime } from '@/features/player/PlayerControls';
import {
  UnifiedTimeline,
  type QualityInterval,
  type ZoneTrendLine,
  type PeakMarker,
  type NoteMarker,
} from '@/features/timeline/UnifiedTimeline';
import { usePlaybackStore } from '@/shared/state/playbackStore';
import { useAuthStore } from '@/shared/state/authStore';

export interface SessionMetadata {
  sessionId: string;
  sourceId: string;
  mediaName: string;
  duration: number;
  imageWidth: number;
  imageHeight: number;
  synthetic: boolean;
  modelProfileId: string;
  modelProfileSha256: string;
  checkpointSha256: string;
  videoSrc: string;
  heatmapUrl?: string | null;
}

interface ReviewWorkspaceProps {
  onBack?: () => void;
  session: SessionMetadata;
  zones: {
    zone_id: string;
    name: string;
    color: string;
    vertices: [number, number][];
  }[];
  activeObservation: CrowdFrameObservation | null;
  activeReadings: ZoneReading[];
  qualityIntervals: QualityInterval[];
  zoneTrends: ZoneTrendLine[];
  peaks?: PeakMarker[];
  initialNotes?: NoteMarker[];
  onAddNote?: (text: string, mediaTime: number) => Promise<void>;
  onDeleteNote?: (noteId: string) => Promise<void>;
  missingFramesCount?: number;
  onSeek?: (time: number) => void;
  onExportCsv?: () => void;
  onExportJsonl?: () => void;
  onEditZones?: () => void;
  onReanalyze?: () => void;
  className?: string;
}

export const ReviewWorkspace: React.FC<ReviewWorkspaceProps> = ({
  onBack,
  session,
  zones,
  activeObservation,
  activeReadings,
  qualityIntervals,
  zoneTrends,
  peaks = [],
  initialNotes = [],
  onAddNote,
  onDeleteNote,
  missingFramesCount = 0,
  onSeek,
  onExportCsv,
  onExportJsonl,
  onEditZones,
  onReanalyze,
  className = '',
}) => {
  const { currentTime, setCurrentTime } = usePlaybackStore();
  const { user } = useAuthStore();
  const isViewer = user?.role === 'VIEWER';
  const [activeTab, setActiveTab] = useState<'zones' | 'peaks' | 'notes' | 'provenance'>('zones');
  const [notes, setNotes] = useState<NoteMarker[]>(initialNotes);
  const [newNoteText, setNewNoteText] = useState('');
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [isSemanticsOpen, setIsSemanticsOpen] = useState(false);

  useEffect(() => {
    setNotes(initialNotes);
  }, [initialNotes]);

  const handleSeek = (time: number) => {
    setCurrentTime(time);
    if (onSeek) onSeek(time);
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNoteText.trim()) return;
    const text = newNoteText.trim();
    const time = currentTime;
    setNewNoteText('');
    if (onAddNote) {
      await onAddNote(text, time);
    } else {
      const newNote: NoteMarker = {
        id: `note-${Date.now()}`,
        time,
        text,
      };
      setNotes((prev) => [...prev, newNote]);
    }
  };

  const handleDeleteNote = async (noteId: string) => {
    if (onDeleteNote) {
      await onDeleteNote(noteId);
    } else {
      setNotes((prev) => prev.filter((n) => n.id !== noteId));
    }
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(label);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  return (
    <div className={`flex flex-col min-h-screen bg-brand-abyssal text-brand-text-primary ${className}`}>
      {/* 1. Mandatory Top Banner: Fail-closed experimental warning */}
      <Banner isSynthetic={session.synthetic} />

      {/* 2. Workspace Navigation & Metadata Header */}
      <header className="flex flex-wrap items-center justify-between gap-4 px-6 py-3 bg-brand-surface border-b border-brand-border">
        <div className="flex items-center gap-3">
          {onBack && (
            <button
              type="button"
              onClick={onBack}
              className="p-1.5 rounded-lg text-brand-text-muted hover:text-brand-text-primary hover:bg-brand-border/60 transition-colors cursor-pointer"
              title="Quay lại danh sách phiên"
              aria-label="Quay lại danh sách phiên"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
          )}
          <div className="p-1.5 bg-brand-gold/10 border border-brand-gold/30 rounded text-brand-gold">
            <Clock className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-semibold text-brand-text-primary">
                {session.mediaName}
              </h1>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-brand-border text-brand-text-muted">
                {session.sessionId.slice(0, 8)}
              </span>
            </div>
            <p className="text-xs text-brand-text-muted">
              Độ phân giải: {session.imageWidth}×{session.imageHeight} • Thời lượng: {formatMediaTime(session.duration)}
            </p>
          </div>
        </div>

        {/* Real Session Status Badge, Semantics modal, Export */}
        <div className="flex items-center gap-2">
          <div
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs border shadow-sm ${
              session.synthetic
                ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
            }`}
            title={session.synthetic ? 'Phiên chạy với dữ liệu mô phỏng (Synthetic)' : 'Phiên phân tích bằng mô hình AI YOLO11 thực'}
          >
            <span className={`w-2 h-2 rounded-full ${session.synthetic ? 'bg-purple-400' : 'bg-emerald-400 animate-pulse'}`} />
            <span className="font-semibold">{session.synthetic ? '🧪 Dữ liệu Mô phỏng' : '🤖 AI Quét Thật (YOLO11)'}</span>
          </div>

          {onEditZones && (
            <button
              type="button"
              disabled={isViewer}
              onClick={() => !isViewer && onEditZones()}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs border transition-colors ${
                isViewer
                  ? 'bg-brand-surface/40 border-brand-border/40 text-brand-text-muted/40 cursor-not-allowed'
                  : 'bg-brand-abyssal hover:bg-brand-border border-brand-border text-brand-text-primary cursor-pointer'
              }`}
              title={isViewer ? 'Khách xem không có quyền chỉnh sửa khu vực' : 'Chỉnh sửa hoặc vẽ lại các khu vực quan sát (Zone Editor)'}
            >
              <Layers className={`w-3.5 h-3.5 ${isViewer ? 'text-brand-text-muted/40' : 'text-brand-gold'}`} />
              <span>Chỉnh sửa khu vực</span>
            </button>
          )}

          {onReanalyze && (
            <button
              type="button"
              disabled={isViewer}
              onClick={() => !isViewer && onReanalyze()}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs border font-medium transition-colors ${
                isViewer
                  ? 'bg-brand-surface/40 border-brand-border/40 text-brand-text-muted/40 cursor-not-allowed'
                  : 'bg-brand-gold/15 hover:bg-brand-gold/25 border-brand-gold/40 text-brand-gold cursor-pointer'
              }`}
              title={isViewer ? 'Khách xem không có quyền chạy lại phân tích' : 'Chạy lại phân tích toàn bộ video này với mô hình AI'}
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Phân tích lại</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => setIsSemanticsOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs bg-brand-abyssal hover:bg-brand-border border border-brand-border text-brand-text-primary transition-colors"
          >
            <Info className="w-3.5 h-3.5 text-brand-gold" />
            <span>Về phép đo này</span>
          </button>
          <SemanticsModal isOpen={isSemanticsOpen} onClose={() => setIsSemanticsOpen(false)} />

          <button
            type="button"
            onClick={onExportCsv}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs bg-brand-abyssal hover:bg-brand-border border border-brand-border text-brand-text-primary transition-colors"
            title="Xuất bảng số đếm theo zone (CSV)"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
            <span>Xuất CSV</span>
          </button>

          <button
            type="button"
            onClick={onExportJsonl}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs bg-brand-abyssal hover:bg-brand-border border border-brand-border text-brand-text-primary transition-colors"
            title="Xuất observations v1 đầy đủ (JSONL)"
          >
            <FileCode className="w-3.5 h-3.5 text-blue-400" />
            <span>Xuất JSONL</span>
          </button>
        </div>
      </header>

      {/* 3. Main Workspace Grid */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 p-6 overflow-hidden">
        {/* Left Column: Player & Timeline (8 of 12 cols) */}
        <section className="lg:col-span-8 flex flex-col gap-4">
          {/* Annotated Video Player */}
          <div className="relative w-full aspect-video bg-black rounded-lg overflow-hidden border border-brand-border shadow-lg">
            <AnnotatedPlayer
              videoSrc={session.videoSrc}
              imageWidth={session.imageWidth}
              imageHeight={session.imageHeight}
              zones={zones}
              observation={activeObservation}
              heatmapUrl={session.heatmapUrl}
              onTimeUpdate={handleSeek}
            />
          </div>

          {/* Transport Controls */}
          <PlayerControls onStepFrame={(delta) => handleSeek(currentTime + delta)} />

          {/* Scrubber & Multi-Tier Quality Timeline */}
          <UnifiedTimeline
            duration={session.duration}
            currentTime={currentTime}
            qualityIntervals={qualityIntervals}
            zoneTrends={zoneTrends}
            peaks={peaks}
            notes={notes}
            missingFramesCount={missingFramesCount}
            onSeek={handleSeek}
          />
        </section>

        {/* Right Column: Zone Readings & Contextual Side Panel (4 of 12 cols) */}
        <section className="lg:col-span-4 flex flex-col gap-4">
          {/* Active Frame Quality Status Card */}
          <div className="p-4 bg-brand-surface border border-brand-border rounded-lg space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-brand-text-muted uppercase tracking-wider">
                Khung hình hiện tại
              </span>
              {activeObservation ? (
                <QualityBadge quality={activeObservation.quality} />
              ) : (
                <QualityBadge quality="UNKNOWN" />
              )}
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-2 bg-brand-abyssal/60 rounded border border-brand-border/60">
                <div className="text-[10px] text-brand-text-muted">Thời gian trôi qua</div>
                <div className="font-mono text-brand-gold font-medium tabular-nums">
                  {formatMediaTime(currentTime)}
                </div>
              </div>
              <div className="p-2 bg-brand-abyssal/60 rounded border border-brand-border/60">
                <div className="text-[10px] text-brand-text-muted">Chỉ số khung</div>
                <div className="font-mono text-brand-text-primary tabular-nums">
                  #{activeObservation?.frame_index ?? 0}
                </div>
              </div>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="flex border-b border-brand-border text-xs">
            <button
              type="button"
              onClick={() => setActiveTab('zones')}
              className={`px-3 py-2 border-b-2 font-medium transition-colors ${
                activeTab === 'zones'
                  ? 'border-brand-gold text-brand-gold'
                  : 'border-transparent text-brand-text-muted hover:text-brand-text-primary'
              }`}
            >
              Vùng quan sát ({zones.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('peaks')}
              className={`px-3 py-2 border-b-2 font-medium transition-colors ${
                activeTab === 'peaks'
                  ? 'border-brand-gold text-brand-gold'
                  : 'border-transparent text-brand-text-muted hover:text-brand-text-primary'
              }`}
            >
              Khoảnh khắc
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('notes')}
              className={`px-3 py-2 border-b-2 font-medium transition-colors ${
                activeTab === 'notes'
                  ? 'border-brand-gold text-brand-gold'
                  : 'border-transparent text-brand-text-muted hover:text-brand-text-primary'
              }`}
            >
              Ghi chú ({notes.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('provenance')}
              className={`px-3 py-2 border-b-2 font-medium transition-colors ${
                activeTab === 'provenance'
                  ? 'border-brand-gold text-brand-gold'
                  : 'border-transparent text-brand-text-muted hover:text-brand-text-primary'
              }`}
            >
              Nguồn gốc
            </button>
          </div>

          {/* Tab Content Area */}
          <div className="flex-1 overflow-y-auto space-y-3 max-h-[500px] pr-1">
            {/* TAB 1: Zones list */}
            {activeTab === 'zones' && (
              <div className="space-y-3">
                {onEditZones && (
                  <div className="flex justify-between items-center px-1">
                    <span className="text-[11px] text-brand-text-muted">Đang theo dõi {zones.length} khu vực</span>
                    <button
                      type="button"
                      onClick={onEditZones}
                      className="text-xs text-brand-gold hover:text-brand-gold-bright flex items-center gap-1 cursor-pointer transition-colors"
                      title="Chỉnh sửa các đỉnh đa giác hoặc vẽ vùng mới"
                    >
                      <Layers className="w-3 h-3" />
                      <span>Chỉnh sửa các vùng này</span>
                    </button>
                  </div>
                )}
                {activeReadings.length === 0 ? (
                  <div className="p-4 bg-brand-surface/40 border border-brand-border rounded text-center text-xs text-brand-text-muted">
                    Chưa có số liệu vùng cho khung hình này.
                  </div>
                ) : (
                  activeReadings.map((reading) => (
                    <ZoneCard key={reading.zoneId} reading={reading} />
                  ))
                )}
              </div>
            )}

            {/* TAB 2: Peaks list */}
            {activeTab === 'peaks' && (
              <div className="space-y-2">
                {peaks.length === 0 ? (
                  <div className="p-4 bg-brand-surface/40 border border-brand-border rounded text-center text-xs text-brand-text-muted">
                    Không có khoảnh khắc cao điểm nổi bật.
                  </div>
                ) : (
                  peaks.map((p, idx) => (
                    <div
                      key={`peak-card-${idx}`}
                      className="p-3 bg-brand-surface border border-brand-border rounded flex items-center justify-between hover:border-brand-gold/40 transition-colors"
                    >
                      <div>
                        <div className="flex items-center gap-1.5 text-xs font-medium text-brand-text-primary">
                          <span className="font-mono text-brand-gold tabular-nums">
                            {p.count} người nhìn thấy
                          </span>
                          <span className="text-[10px] text-brand-text-muted">
                            ({p.label ?? p.zoneId})
                          </span>
                        </div>
                        <div className="text-[11px] text-brand-text-muted mt-0.5">
                          Thời điểm: {formatMediaTime(p.time)}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleSeek(p.time)}
                        className="px-2 py-1 text-[11px] bg-brand-abyssal border border-brand-border hover:border-brand-gold/50 rounded text-brand-text-primary transition-colors"
                      >
                        Tua tới
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* TAB 3: Notes list & Add note form */}
            {activeTab === 'notes' && (
              <div className="space-y-3">
                {isViewer ? (
                  <div className="p-2.5 rounded bg-brand-surface/60 border border-brand-border/60 text-[11px] text-brand-text-muted">
                    Chế độ Khách xem: Bạn có thể đọc các ghi chú giám sát nhưng không có quyền tạo hoặc xóa ghi chú.
                  </div>
                ) : (
                  <form onSubmit={handleAddNote} className="space-y-2">
                    <div className="flex items-center justify-between text-xs text-brand-text-muted">
                      <span>Thêm ghi chú tại thời điểm:</span>
                      <span className="font-mono text-brand-gold tabular-nums">
                        {formatMediaTime(currentTime)}
                      </span>
                    </div>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={newNoteText}
                        onChange={(e) => setNewNoteText(e.target.value)}
                        placeholder="Nội dung ghi chú của người vận hành..."
                        className="flex-1 px-3 py-1.5 bg-brand-abyssal border border-brand-border rounded text-xs text-brand-text-primary focus:border-brand-gold outline-none"
                      />
                      <button
                        type="submit"
                        disabled={!newNoteText.trim()}
                        className="px-3 py-1.5 bg-brand-gold hover:bg-brand-gold/90 disabled:opacity-40 text-brand-abyssal font-medium rounded text-xs flex items-center gap-1 cursor-pointer"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        Lưu
                      </button>
                    </div>
                  </form>
                )}

                <div className="space-y-2 pt-2 border-t border-brand-border/60">
                  {notes.map((note) => (
                    <div
                      key={note.id}
                      className="p-2.5 bg-brand-surface border border-brand-border rounded text-xs flex items-start justify-between gap-2"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-cyan-400 text-[11px] tabular-nums">
                            {formatMediaTime(note.time)}
                          </span>
                        </div>
                        <p className="text-brand-text-primary">{note.text}</p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          type="button"
                          onClick={() => handleSeek(note.time)}
                          className="text-[10px] text-brand-text-muted hover:text-brand-gold underline shrink-0 cursor-pointer"
                        >
                          Tua tới
                        </button>
                        {!isViewer && (
                          <button
                            type="button"
                            onClick={() => handleDeleteNote(note.id)}
                            className="p-1 text-brand-text-muted hover:text-red-400 rounded transition-colors cursor-pointer"
                            title="Xóa ghi chú"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB 4: Provenance Information */}
            {activeTab === 'provenance' && (
              <div className="p-3 bg-brand-surface border border-brand-border rounded-lg space-y-3 text-xs">
                <div className="space-y-1">
                  <div className="text-[10px] text-brand-text-muted">Mã hồ sơ mô hình (model_profile_id)</div>
                  <div className="font-mono text-brand-text-primary bg-brand-abyssal p-1.5 rounded border border-brand-border">
                    {session.modelProfileId}
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="flex items-center justify-between text-[10px] text-brand-text-muted">
                    <span>Mã băm Profile (SHA-256)</span>
                    <button
                      type="button"
                      onClick={() => copyToClipboard(session.modelProfileSha256, 'profile')}
                      className="flex items-center gap-1 text-brand-gold hover:underline"
                    >
                      {copiedHash === 'profile' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                      <span>{copiedHash === 'profile' ? 'Đã sao chép' : 'Sao chép'}</span>
                    </button>
                  </div>
                  <div className="font-mono text-[10px] text-brand-text-muted bg-brand-abyssal p-1.5 rounded border border-brand-border break-all">
                    {session.modelProfileSha256}
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="flex items-center justify-between text-[10px] text-brand-text-muted">
                    <span>Mã băm Trọng số Checkpoint (SHA-256)</span>
                    <button
                      type="button"
                      onClick={() => copyToClipboard(session.checkpointSha256, 'checkpoint')}
                      className="flex items-center gap-1 text-brand-gold hover:underline"
                    >
                      {copiedHash === 'checkpoint' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                      <span>{copiedHash === 'checkpoint' ? 'Đã sao chép' : 'Sao chép'}</span>
                    </button>
                  </div>
                  <div className="font-mono text-[10px] text-brand-text-muted bg-brand-abyssal p-1.5 rounded border border-brand-border break-all">
                    {session.checkpointSha256}
                  </div>
                </div>

                <div className="pt-2 border-t border-brand-border/60 text-[11px] text-brand-text-muted flex items-center gap-1.5">
                  <ShieldAlert className="w-4 h-4 text-brand-gold shrink-0" />
                  <span>
                    Chế độ: <strong className="text-brand-text-primary">EXPERIMENTAL_NO_APPROVAL</strong>. Cảnh báo vận hành bị chặn hoàn toàn.
                  </span>
                </div>
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
};
