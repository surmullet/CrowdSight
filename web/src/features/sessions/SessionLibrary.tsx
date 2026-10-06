import React, { useState, useMemo } from 'react';
import {
  Search,
  Plus,
  Play,
  Trash2,
  AlertTriangle,
  Clock,
  Film,
  Layers,
  Sparkles,
  LayoutGrid,
  List as ListIcon,
  RotateCcw,
} from 'lucide-react';
import { Banner } from '@/shared/ui/Banner';
import { formatMediaTime } from '@/features/player/PlayerControls';
import { useLanguage } from '@/shared/i18n/LanguageContext';

export interface SessionSummaryItem {
  id: string;
  sourceId: string;
  mediaName: string;
  duration: number;
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLING' | 'CANCELLED';
  progress: number;
  synthetic: boolean;
  createdAt: string;
  zoneSetName?: string;
  zoneSetVersionId?: string;
  videoSrc?: string;
  qualityBreakdown?: {
    validPct: number;
    partialPct: number;
    unknownPct: number;
    stalePct: number;
  };
}

interface SessionLibraryProps {
  sessions: SessionSummaryItem[];
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onDeleteSession: (id: string) => Promise<void>;
  onReanalyzeSession?: (session: SessionSummaryItem) => void;
  isLoading?: boolean;
  className?: string;
}

export const SessionLibrary: React.FC<SessionLibraryProps> = ({
  sessions,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  onReanalyzeSession,
  isLoading = false,
  className = '',
}) => {
  const { locale, t } = useLanguage();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [sessionToDelete, setSessionToDelete] = useState<SessionSummaryItem | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const filteredSessions = useMemo(() => {
    return sessions.filter((s) => {
      const matchesSearch =
        s.mediaName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (s.zoneSetName && s.zoneSetName.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchesStatus =
        statusFilter === 'ALL' ||
        s.status === statusFilter ||
        (statusFilter === 'ACTIVE' && (s.status === 'RUNNING' || s.status === 'QUEUED'));

      return matchesSearch && matchesStatus;
    });
  }, [sessions, searchQuery, statusFilter]);

  const handleDeleteConfirm = async () => {
    if (!sessionToDelete) return;
    setIsDeleting(true);
    try {
      await onDeleteSession(sessionToDelete.id);
      setSessionToDelete(null);
    } catch {
      // Đã được xử lý và hiển thị thông báo trong onDeleteSession
    } finally {
      setIsDeleting(false);
    }
  };

  const getStatusBadge = (status: SessionSummaryItem['status']) => {
    switch (status) {
      case 'COMPLETED':
        return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">{locale === 'vi' ? 'Hoàn tất' : 'Completed'}</span>;
      case 'RUNNING':
        return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-blue-500/10 text-blue-400 border border-blue-500/30 animate-pulse">{locale === 'vi' ? 'Đang chạy' : 'Running'}</span>;
      case 'QUEUED':
        return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-500/10 text-slate-400 border border-slate-500/30">{locale === 'vi' ? 'Chờ xử lý' : 'Queued'}</span>;
      case 'FAILED':
        return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-red-500/10 text-red-400 border border-red-500/30">{locale === 'vi' ? 'Thất bại' : 'Failed'}</span>;
      case 'CANCELLED':
      case 'CANCELLING':
        return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30">{locale === 'vi' ? 'Đã hủy' : 'Cancelled'}</span>;
    }
  };

  return (
    <div className={`flex flex-col min-h-screen bg-brand-abyssal text-brand-text-primary ${className}`}>
      {/* 1. Mandatory Top Banner */}
      <Banner />

      {/* 2. Top Header & Primary Action */}
      <header className="px-8 py-5 border-b border-brand-border bg-brand-surface/40 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-brand-text-primary">
            {t.sessions.title}
          </h1>
          <p className="text-xs text-brand-text-muted mt-0.5">
            {t.sessions.subtitle}
          </p>
        </div>

        <button
          type="button"
          onClick={onNewSession}
          className="flex items-center gap-2 px-4 py-2 bg-brand-gold hover:bg-brand-gold/90 text-brand-abyssal font-semibold text-xs rounded-lg transition-colors shadow"
        >
          <Plus className="w-4 h-4" />
          <span>{t.sessions.newSession}</span>
        </button>
      </header>

      {/* 3. Toolbar: Search, Filters & View Toggle */}
      <div className="px-8 py-4 border-b border-brand-border/60 bg-brand-abyssal flex flex-wrap items-center justify-between gap-3 text-xs">
        {/* Search */}
        <div className="relative flex-1 min-w-[240px] max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-brand-text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t.sessions.searchPlaceholder}
            className="w-full pl-9 pr-4 py-1.5 bg-brand-surface border border-brand-border rounded-lg text-brand-text-primary placeholder:text-brand-text-muted/60 focus:border-brand-gold outline-none"
          />
        </div>

        {/* Status Filter Pills */}
        <div className="flex items-center gap-1.5 bg-brand-surface p-1 rounded-lg border border-brand-border">
          {[
            { key: 'ALL', label: t.sessions.filters.all },
            { key: 'COMPLETED', label: t.sessions.filters.completed },
            { key: 'ACTIVE', label: t.sessions.filters.active },
            { key: 'FAILED', label: t.sessions.filters.failed },
            { key: 'CANCELLED', label: t.sessions.filters.cancelled },
          ].map((pill) => (
            <button
              key={pill.key}
              type="button"
              onClick={() => setStatusFilter(pill.key)}
              className={`px-3 py-1 rounded text-xs transition-colors ${
                statusFilter === pill.key
                  ? 'bg-brand-abyssal text-brand-gold font-medium border border-brand-gold/40'
                  : 'text-brand-text-muted hover:text-brand-text-primary'
              }`}
            >
              {pill.label}
            </button>
          ))}
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center gap-1 border border-brand-border rounded-lg p-1 bg-brand-surface">
          <button
            type="button"
            onClick={() => setViewMode('grid')}
            className={`p-1 rounded ${viewMode === 'grid' ? 'bg-brand-abyssal text-brand-gold' : 'text-brand-text-muted'}`}
            title="Dạng lưới"
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => setViewMode('list')}
            className={`p-1 rounded ${viewMode === 'list' ? 'bg-brand-abyssal text-brand-gold' : 'text-brand-text-muted'}`}
            title="Dạng danh sách"
          >
            <ListIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 4. Content Area */}
      <main className="flex-1 p-8">
        {isLoading ? (
          <div className="flex items-center justify-center p-16 text-xs text-brand-text-muted">
            Đang tải danh sách phiên...
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-16 text-center border border-dashed border-brand-border rounded-xl bg-brand-surface/20">
            <Film className="w-12 h-12 text-brand-text-muted/40 mb-3" />
            <h3 className="text-sm font-semibold text-brand-text-primary">
              Không tìm thấy phiên phân tích nào
            </h3>
            <p className="text-xs text-brand-text-muted max-w-sm mt-1 mb-4">
              Chưa có phiên phân tích nào khớp với bộ lọc, hoặc chưa có video nào được xử lý.
            </p>
            <button
              type="button"
              onClick={onNewSession}
              className="px-4 py-2 bg-brand-gold text-brand-abyssal font-medium text-xs rounded-lg hover:bg-brand-gold/90 transition-colors"
            >
              Tạo phiên đầu tiên
            </button>
          </div>
        ) : viewMode === 'grid' ? (
          /* GRID VIEW */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredSessions.map((session) => (
              <div
                key={session.id}
                className="group relative flex flex-col justify-between bg-brand-surface border border-brand-border hover:border-brand-gold/50 rounded-xl p-5 transition-all shadow-sm"
              >
                <div>
                  {/* Card Header: Badges & Status */}
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {getStatusBadge(session.status)}
                      {session.synthetic && (
                        <span className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-purple-500/10 text-purple-300 border border-purple-500/30 font-medium">
                          <Sparkles className="w-2.5 h-2.5" />
                          Mô phỏng
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] font-mono text-brand-text-muted">
                      {session.id.slice(0, 8)}
                    </span>
                  </div>

                  {/* Media Name */}
                  <h3 className="font-semibold text-sm text-brand-text-primary group-hover:text-brand-gold transition-colors line-clamp-1">
                    {session.mediaName}
                  </h3>

                  {/* Metadata: Duration & Zone set */}
                  <div className="flex items-center gap-4 text-xs text-brand-text-muted mt-2">
                    <span className="flex items-center gap-1 font-mono tabular-nums">
                      <Clock className="w-3.5 h-3.5" />
                      {formatMediaTime(session.duration)}
                    </span>
                    {session.zoneSetName && (
                      <span className="flex items-center gap-1">
                        <Layers className="w-3.5 h-3.5" />
                        {session.zoneSetName}
                      </span>
                    )}
                  </div>

                  {/* Micro Quality Breakdown Ribbon */}
                  {session.qualityBreakdown && (
                    <div className="mt-4 space-y-1">
                      <div className="flex justify-between text-[10px] text-brand-text-muted">
                        <span>Chất lượng khung hình</span>
                        <span>{session.qualityBreakdown.validPct}% VALID</span>
                      </div>
                      <div className="w-full h-2 rounded bg-brand-abyssal flex overflow-hidden border border-brand-border/60">
                        <div
                          style={{ width: `${session.qualityBreakdown.validPct}%` }}
                          className="bg-emerald-500/70"
                          title={`VALID: ${session.qualityBreakdown.validPct}%`}
                        />
                        <div
                          style={{ width: `${session.qualityBreakdown.partialPct}%` }}
                          className="pattern-diagonal-hatching bg-amber-500/60"
                          title={`PARTIAL: ${session.qualityBreakdown.partialPct}%`}
                        />
                        <div
                          style={{ width: `${session.qualityBreakdown.unknownPct}%` }}
                          className="pattern-dot-stipple bg-slate-600"
                          title={`UNKNOWN: ${session.qualityBreakdown.unknownPct}%`}
                        />
                        <div
                          style={{ width: `${session.qualityBreakdown.stalePct}%` }}
                          className="bg-red-500/70"
                          title={`STALE: ${session.qualityBreakdown.stalePct}%`}
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* Card Actions */}
                <div className="flex items-center justify-between pt-4 mt-4 border-t border-brand-border/60">
                  <button
                    type="button"
                    onClick={() => setSessionToDelete(session)}
                    className="p-1.5 rounded text-brand-text-muted hover:text-red-400 hover:bg-red-500/10 transition-colors"
                    title="Xóa phiên phân tích"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>

                  <div className="flex items-center gap-2">
                    {onReanalyzeSession && (
                      <button
                        type="button"
                        onClick={() => onReanalyzeSession(session)}
                        className="flex items-center gap-1.5 px-2.5 py-1.5 bg-brand-surface hover:bg-brand-gold/10 hover:border-brand-gold/40 border border-brand-border rounded-lg text-xs font-medium text-brand-text-muted hover:text-brand-gold transition-all"
                        title="Phân tích lại video này bằng mô hình AI"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                        <span>Phân tích lại</span>
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={() => onSelectSession(session.id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-abyssal hover:bg-brand-gold hover:text-brand-abyssal border border-brand-border rounded-lg text-xs font-medium text-brand-text-primary transition-all"
                    >
                      <Play className="w-3.5 h-3.5 fill-current" />
                      <span>Xem kết quả</span>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          /* LIST VIEW */
          <div className="border border-brand-border rounded-xl bg-brand-surface overflow-hidden text-xs">
            <table className="w-full text-left">
              <thead className="bg-brand-abyssal/60 border-b border-brand-border text-brand-text-muted">
                <tr>
                  <th className="py-3 px-4 font-medium">Phiên</th>
                  <th className="py-3 px-4 font-medium">Trạng thái</th>
                  <th className="py-3 px-4 font-medium">Thời lượng</th>
                  <th className="py-3 px-4 font-medium">Tập vùng</th>
                  <th className="py-3 px-4 font-medium">Ngày tạo</th>
                  <th className="py-3 px-4 font-medium text-right">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-border/60">
                {filteredSessions.map((s) => (
                  <tr key={s.id} className="hover:bg-brand-abyssal/40 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-semibold text-brand-text-primary">{s.mediaName}</div>
                      <div className="font-mono text-[10px] text-brand-text-muted">{s.id.slice(0, 12)}</div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5">
                        {getStatusBadge(s.status)}
                        {s.synthetic && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-purple-500/10 text-purple-300 border border-purple-500/30">
                            Mô phỏng
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 font-mono tabular-nums text-brand-text-muted">
                      {formatMediaTime(s.duration)}
                    </td>
                    <td className="py-3 px-4 text-brand-text-muted">
                      {s.zoneSetName || '—'}
                    </td>
                    <td className="py-3 px-4 text-brand-text-muted">
                      {s.createdAt}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => setSessionToDelete(s)}
                          className="p-1 rounded text-brand-text-muted hover:text-red-400"
                          title="Xóa phiên"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                        {onReanalyzeSession && (
                          <button
                            type="button"
                            onClick={() => onReanalyzeSession(s)}
                            className="p-1 rounded text-brand-text-muted hover:text-brand-gold"
                            title="Phân tích lại video này"
                          >
                            <RotateCcw className="w-4 h-4" />
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => onSelectSession(s.id)}
                          className="px-2.5 py-1 bg-brand-abyssal hover:bg-brand-gold hover:text-brand-abyssal border border-brand-border rounded font-medium"
                        >
                          Xem
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

      {/* 5. Delete Confirmation Modal (Explains permanent cascade deletion of artifacts) */}
      {sessionToDelete && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm"
        >
          <div className="bg-brand-surface border border-brand-border rounded-xl max-w-md w-full p-6 shadow-2xl text-xs space-y-4">
            <div className="flex items-center gap-3 text-red-400">
              <div className="p-2 bg-red-500/10 border border-red-500/30 rounded-lg">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-brand-text-primary">
                  Xác nhận xóa phiên phân tích
                </h3>
                <p className="text-[11px] text-brand-text-muted">
                  Thao tác này không thể hoàn tác
                </p>
              </div>
            </div>

            <p className="text-brand-text-primary leading-relaxed">
              Bạn có chắc chắn muốn xóa phiên <strong className="text-brand-gold">{sessionToDelete.mediaName}</strong> (ID: {sessionToDelete.id.slice(0, 8)})?
            </p>

            <div className="p-3 bg-red-950/20 border border-red-900/40 rounded-lg text-red-300 text-[11px] leading-relaxed">
              ⚠️ <strong>Cảnh báo:</strong> Cơ sở dữ liệu và toàn bộ tệp kết quả (video proxy H.264, heat map RGBA, tệp xuất JSONL/CSV) lưu trên máy chủ sẽ bị xóa vĩnh viễn khỏi bộ nhớ lưu trữ.
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setSessionToDelete(null)}
                disabled={isDeleting}
                className="px-4 py-2 bg-brand-abyssal hover:bg-brand-border border border-brand-border text-brand-text-primary rounded-lg transition-colors"
              >
                Hủy
              </button>
              <button
                type="button"
                onClick={handleDeleteConfirm}
                disabled={isDeleting}
                className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white font-medium rounded-lg transition-colors flex items-center gap-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>{isDeleting ? 'Đang xóa...' : 'Xóa vĩnh viễn'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
