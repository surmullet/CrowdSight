import React, { useState, useEffect } from 'react';
import {
  Printer,
  FileSpreadsheet,
  X,
  FileText,
  TrendingUp,
  Clock,
  Layers,
  Calendar,
  Shield,
  Activity,
  ArrowUpRight,
  ArrowDownRight,
  ArrowLeft,
} from 'lucide-react';
import {
  type SessionReportData,
  exportSessionToExcel,
  formatTime,
} from './reportUtils';

interface ExecutiveReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  reportData: SessionReportData;
  onSeek?: (time: number) => void;
}

export const ExecutiveReportModal: React.FC<ExecutiveReportModalProps> = ({
  isOpen,
  onClose,
  reportData,
  onSeek,
}) => {
  const [activeTab, setActiveTab] = useState<'document' | 'comparison'>('document');
  const [hoveredTrendIndex, setHoveredTrendIndex] = useState<number | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handlePrint = () => {
    window.print();
  };

  const handleExcelExport = () => {
    exportSessionToExcel(reportData);
  };

  // SVG dimensions for Multi-Zone Trend Chart
  const svgWidth = 720;
  const svgHeight = 220;
  const padding = { top: 25, right: 30, bottom: 35, left: 45 };
  const chartW = svgWidth - padding.left - padding.right;
  const chartH = svgHeight - padding.top - padding.bottom;

  const maxVal = Math.max(1, reportData.overallPeakCount);
  const duration = Math.max(1, reportData.session.duration);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-black/80 backdrop-blur-md print:p-0 print:bg-white print:static print:inset-auto"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        style={{ backgroundColor: '#111724' }}
        className="w-full max-w-5xl h-[92vh] flex flex-col rounded-2xl border border-[#26354A] shadow-2xl overflow-hidden print:border-none print:shadow-none print:h-auto print:max-w-none print:rounded-none print:bg-white"
      >
        {/* --- 1. MODAL TOP TOOLBAR (Hidden in Print) --- */}
        <header
          style={{ backgroundColor: '#161F2E' }}
          className="px-6 py-3.5 border-b border-[#243346] flex flex-wrap items-center justify-between gap-3 shrink-0 print:hidden"
        >
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#1C283C] hover:bg-[#253752] border border-[#2B3E5C] text-brand-text-primary hover:text-white font-medium text-xs transition-colors cursor-pointer shadow-sm"
              title="Quay lại màn hình giám sát cũ (ESC)"
              aria-label="Quay lại màn cũ"
            >
              <ArrowLeft className="w-4 h-4 text-brand-gold" />
              <span className="font-semibold">Quay lại màn cũ</span>
            </button>
            <div className="p-2 rounded-xl bg-brand-gold/15 text-brand-gold border border-brand-gold/30">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-brand-text-primary flex items-center gap-2">
                <span>Báo Cáo Phân Tích & Giám Sát Đám Đông</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-brand-gold/15 text-brand-gold border border-brand-gold/30">
                  {reportData.session.sessionId.slice(0, 8)}
                </span>
              </h2>
              <p className="text-[11px] text-brand-text-muted mt-0.5">
                {reportData.session.mediaName} • {formatTime(reportData.session.duration)}
              </p>
            </div>
          </div>

          {/* Tab Selector & Primary Actions */}
          <div className="flex items-center gap-2">
            <div
              style={{ backgroundColor: '#101724' }}
              className="flex items-center p-1 rounded-xl border border-[#243346] mr-2"
            >
              <button
                type="button"
                onClick={() => setActiveTab('document')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                  activeTab === 'document'
                    ? 'bg-[#1D293C] text-brand-gold font-bold shadow-sm'
                    : 'text-brand-text-muted hover:text-brand-text-primary'
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Báo cáo tổng hợp</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('comparison')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                  activeTab === 'comparison'
                    ? 'bg-[#1D293C] text-brand-gold font-bold shadow-sm'
                    : 'text-brand-text-muted hover:text-brand-text-primary'
                }`}
              >
                <TrendingUp className="w-3.5 h-3.5" />
                <span>So sánh đa vùng</span>
              </button>
            </div>

            <button
              type="button"
              onClick={handlePrint}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-brand-gold hover:bg-brand-gold/90 text-brand-abyssal font-bold text-xs shadow transition-colors cursor-pointer"
              title="In trực tiếp hoặc Lưu dưới dạng PDF"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>In / Lưu PDF</span>
            </button>

            <button
              type="button"
              onClick={handleExcelExport}
              style={{ backgroundColor: '#182436' }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/10 font-medium text-xs transition-colors cursor-pointer"
              title="Tải file Excel đa trang tính (.xlsx)"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              <span>Xuất Excel (.xlsx)</span>
            </button>

            <button
              type="button"
              onClick={onClose}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-xl text-brand-text-muted hover:text-white hover:bg-[#1E2B3E] border border-transparent hover:border-[#2D3F58] transition-colors ml-1 cursor-pointer"
              title="Đóng báo cáo (ESC)"
              aria-label="Đóng"
            >
              <X className="w-4 h-4" />
              <span className="text-xs">Đóng</span>
            </button>
          </div>
        </header>

        {/* --- 2. MODAL CONTENT BODY --- */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6 text-xs text-brand-text-primary print:p-0 print:overflow-visible print:text-black">
          {/* TAB 1: EXECUTIVE DOCUMENT VIEW (Printable) */}
          {activeTab === 'document' && (
            <div className="space-y-6 max-w-4xl mx-auto print:space-y-4">
              {/* Document Header */}
              <div
                style={{ backgroundColor: '#141D2C' }}
                className="p-6 rounded-2xl border border-[#25354A] flex flex-wrap items-center justify-between gap-4 print:bg-white print:border-b print:border-gray-300 print:rounded-none print:p-0 print:pb-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-lg text-brand-gold tracking-tight print:text-blue-900">
                      CrowdSight Analytics
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 print:border-gray-400 print:text-gray-700">
                      BÁO CÁO PHÂN TÍCH VẬN HÀNH
                    </span>
                  </div>
                  <h1 className="text-base font-bold text-brand-text-primary print:text-black">
                    Bản Báo Cáo Giám Sát Phân Vùng Đám Đông
                  </h1>
                  <p className="text-[11px] text-brand-text-muted print:text-gray-600">
                    Nguồn video: <strong className="text-brand-text-primary print:text-black">{reportData.session.mediaName}</strong>
                  </p>
                </div>

                <div className="text-right space-y-1 text-[11px] text-brand-text-muted print:text-gray-600">
                  <p className="flex items-center justify-end gap-1.5 font-mono">
                    <Calendar className="w-3.5 h-3.5 text-brand-gold" />
                    <span>{new Date().toLocaleDateString('vi-VN')}</span>
                  </p>
                  <p className="font-mono text-[10px]">
                    ID: {reportData.session.sessionId}
                  </p>
                  <p className="text-[10px] text-amber-400 print:text-gray-500 font-medium">
                    CHỈ LƯU HÀNH NỘI BỘ
                  </p>
                </div>
              </div>

              {/* KPI Summary Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 print:grid-cols-4 print:gap-2">
                <div
                  style={{ backgroundColor: '#141C2B' }}
                  className="p-4 rounded-xl border border-[#243346] print:bg-gray-50 print:border-gray-300"
                >
                  <div className="text-[10px] text-brand-text-muted uppercase font-mono print:text-gray-600">
                    Đỉnh Quan Sát
                  </div>
                  <div className="text-2xl font-bold font-mono text-brand-gold mt-1 print:text-blue-900">
                    {reportData.overallPeakCount}
                  </div>
                  <div className="text-[10px] text-brand-text-muted mt-0.5 print:text-gray-500">
                    người tại {formatTime(reportData.overallPeakTime)}
                  </div>
                </div>

                <div
                  style={{ backgroundColor: '#141C2B' }}
                  className="p-4 rounded-xl border border-[#243346] print:bg-gray-50 print:border-gray-300"
                >
                  <div className="text-[10px] text-brand-text-muted uppercase font-mono print:text-gray-600">
                    Số Khu Vực
                  </div>
                  <div className="text-2xl font-bold font-mono text-cyan-400 mt-1 print:text-gray-900">
                    {reportData.zones.length}
                  </div>
                  <div className="text-[10px] text-brand-text-muted mt-0.5 print:text-gray-500">
                    khu vực giám sát
                  </div>
                </div>

                <div
                  style={{ backgroundColor: '#141C2B' }}
                  className="p-4 rounded-xl border border-[#243346] print:bg-gray-50 print:border-gray-300"
                >
                  <div className="text-[10px] text-brand-text-muted uppercase font-mono print:text-gray-600">
                    Thời Lượng
                  </div>
                  <div className="text-2xl font-bold font-mono text-emerald-400 mt-1 print:text-gray-900">
                    {formatTime(reportData.session.duration)}
                  </div>
                  <div className="text-[10px] text-brand-text-muted mt-0.5 print:text-gray-500">
                    {reportData.session.duration.toFixed(1)}s video
                  </div>
                </div>

                <div
                  style={{ backgroundColor: '#141C2B' }}
                  className="p-4 rounded-xl border border-[#243346] print:bg-gray-50 print:border-gray-300"
                >
                  <div className="text-[10px] text-brand-text-muted uppercase font-mono print:text-gray-600">
                    Độ Tin Cậy Khung Hình
                  </div>
                  <div className="text-2xl font-bold font-mono text-purple-400 mt-1 print:text-gray-900">
                    {reportData.qualityBreakdown.validPct}%
                  </div>
                  <div className="text-[10px] text-brand-text-muted mt-0.5 print:text-gray-500">
                    khung hình VALID
                  </div>
                </div>
              </div>

              {/* Section 1: Multi-Zone Comparison & Distribution */}
              <div
                style={{ backgroundColor: '#141D2C' }}
                className="p-5 rounded-2xl border border-[#243346] space-y-4 print:bg-white print:border-gray-300"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Layers className="w-4 h-4 text-brand-gold print:text-blue-900" />
                    <h3 className="font-bold text-sm text-brand-text-primary print:text-black">
                      1. So Sánh Mật Độ Tương Đối & Phân Bổ Giữa Các Vùng
                    </h3>
                  </div>
                  <span className="text-[10px] text-brand-text-muted print:text-gray-500">
                    Tỷ trọng trên tổng lượt quan sát
                  </span>
                </div>

                {/* Relative Distribution Visual Bar */}
                <div className="space-y-1.5">
                  <div className="flex justify-between text-[11px] text-brand-text-muted print:text-gray-600">
                    <span>Tỷ lệ phân bổ giữa các khu vực:</span>
                    <span className="font-mono">100% Tổng thể</span>
                  </div>
                  <div className="w-full h-3 rounded-lg overflow-hidden flex border border-[#25354A] print:border-gray-300">
                    {reportData.zoneSummaries.map((zs) => (
                      <div
                        key={zs.zoneId}
                        style={{ width: `${zs.sharePct}%`, backgroundColor: zs.color }}
                        className="h-full transition-all"
                        title={`${zs.name}: ${zs.sharePct}%`}
                      />
                    ))}
                  </div>
                </div>

                {/* Zone Comparison Table */}
                <div className="overflow-x-auto rounded-xl border border-[#243346] print:border-gray-300">
                  <table className="w-full text-left text-xs">
                    <thead
                      style={{ backgroundColor: '#111722' }}
                      className="border-b border-[#243346] text-brand-text-muted print:bg-gray-100 print:text-gray-700"
                    >
                      <tr>
                        <th className="py-2.5 px-3 font-semibold">Khu vực giám sát</th>
                        <th className="py-2.5 px-3 font-semibold text-center">Đỉnh quan sát (Peak)</th>
                        <th className="py-2.5 px-3 font-semibold text-center">Thời điểm đỉnh</th>
                        <th className="py-2.5 px-3 font-semibold text-center">Trung bình (Avg)</th>
                        <th className="py-2.5 px-3 font-semibold text-center">Thấp nhất (Min)</th>
                        <th className="py-2.5 px-3 font-semibold text-right">Tỷ trọng tương đối</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#202E40] print:divide-gray-200">
                      {reportData.zoneSummaries.map((zs) => (
                        <tr key={zs.zoneId} className="hover:bg-[#182335]/50 print:hover:bg-transparent">
                          <td className="py-2.5 px-3">
                            <div className="flex items-center gap-2">
                              <span
                                className="w-3 h-3 rounded-full border border-white/20 shrink-0"
                                style={{ backgroundColor: zs.color }}
                              />
                              <span className="font-semibold text-brand-text-primary print:text-black">
                                {zs.name}
                              </span>
                            </div>
                          </td>
                          <td className="py-2.5 px-3 text-center font-mono font-bold text-brand-gold print:text-blue-900">
                            {zs.maxCount} người
                          </td>
                          <td className="py-2.5 px-3 text-center font-mono text-brand-text-muted print:text-gray-700">
                            {formatTime(zs.peakTime)}
                          </td>
                          <td className="py-2.5 px-3 text-center font-mono text-brand-text-primary print:text-black">
                            {zs.avgCount}
                          </td>
                          <td className="py-2.5 px-3 text-center font-mono text-brand-text-muted print:text-gray-600">
                            {zs.minCount}
                          </td>
                          <td className="py-2.5 px-3 text-right">
                            <span className="font-mono font-bold px-2 py-0.5 rounded text-[11px] bg-brand-gold/15 text-brand-gold border border-brand-gold/30 print:border-gray-400 print:text-gray-900">
                              {zs.sharePct}%
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Section 2: Surge Events & Sudden Fluctuations */}
              <div
                style={{ backgroundColor: '#141D2C' }}
                className="p-5 rounded-2xl border border-[#243346] space-y-3 print:bg-white print:border-gray-300"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-amber-400 print:text-amber-700" />
                    <h3 className="font-bold text-sm text-brand-text-primary print:text-black">
                      2. Sự Kiện Biến Động Đột Biến (Surge Events & Spikes)
                    </h3>
                  </div>
                  <span className="text-[10px] text-brand-text-muted print:text-gray-500">
                    Phát hiện khi số đếm chênh lệch ≥ 3 người
                  </span>
                </div>

                {reportData.surgeEvents.length === 0 ? (
                  <p className="text-xs text-brand-text-muted italic py-2">
                    Không ghi nhận biến động đột biến bất thường vượt ngưỡng trong phiên này. Mật độ diễn ra tương đối ổn định.
                  </p>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 print:grid-cols-2">
                    {reportData.surgeEvents.slice(0, 6).map((se, idx) => (
                      <div
                        key={idx}
                        style={{ backgroundColor: '#101622' }}
                        className="p-2.5 rounded-xl border border-[#243346] flex items-center justify-between print:bg-gray-50 print:border-gray-200"
                      >
                        <div className="flex items-center gap-2">
                          {se.type === 'SPIKE_UP' ? (
                            <div className="p-1 rounded bg-amber-500/15 text-amber-400 border border-amber-500/30 print:text-amber-800">
                              <ArrowUpRight className="w-3.5 h-3.5" />
                            </div>
                          ) : (
                            <div className="p-1 rounded bg-blue-500/15 text-blue-400 border border-blue-500/30 print:text-blue-800">
                              <ArrowDownRight className="w-3.5 h-3.5" />
                            </div>
                          )}
                          <div>
                            <div className="font-semibold text-xs text-brand-text-primary print:text-black">
                              {se.zoneName}
                            </div>
                            <div className="text-[10px] text-brand-text-muted print:text-gray-600 font-mono">
                              Thời điểm: {formatTime(se.time)} ({se.previousCount} → {se.currentCount} người)
                            </div>
                          </div>
                        </div>

                        <div className="text-right">
                          <span
                            className={`font-mono text-xs font-bold px-1.5 py-0.5 rounded ${
                              se.type === 'SPIKE_UP'
                                ? 'text-amber-400 bg-amber-500/10 print:text-amber-800'
                                : 'text-blue-400 bg-blue-500/10 print:text-blue-800'
                            }`}
                          >
                            {se.delta > 0 ? `+${se.delta}` : se.delta} người
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Section 3: Operator Notes Log */}
              {reportData.notes.length > 0 && (
                <div
                  style={{ backgroundColor: '#141D2C' }}
                  className="p-5 rounded-2xl border border-[#243346] space-y-3 print:bg-white print:border-gray-300"
                >
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-brand-gold print:text-blue-900" />
                    <h3 className="font-bold text-sm text-brand-text-primary print:text-black">
                      3. Nhật Ký Ghi Chú Hiện Trường Của Giám Sát Viên ({reportData.notes.length})
                    </h3>
                  </div>

                  <div className="space-y-2">
                    {reportData.notes.map((note) => (
                      <div
                        key={note.id}
                        style={{ backgroundColor: '#101622' }}
                        className="p-2.5 rounded-xl border border-[#243346] flex items-start gap-3 print:bg-gray-50 print:border-gray-200"
                      >
                        <span className="font-mono text-cyan-400 font-bold text-[11px] shrink-0 print:text-blue-800">
                          {formatTime(note.time)}
                        </span>
                        <p className="text-brand-text-primary text-xs print:text-black">
                          {note.text}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Section 4: AI Model Provenance & Compliance */}
              <div
                style={{ backgroundColor: '#101724' }}
                className="p-4 rounded-xl border border-[#243346] text-[11px] text-brand-text-muted space-y-1.5 print:bg-gray-50 print:border-gray-300 print:text-gray-700"
              >
                <div className="flex items-center gap-1.5 font-bold text-brand-gold print:text-blue-900">
                  <Shield className="w-3.5 h-3.5" />
                  <span>Truy Xuất Nguồn Gốc AI & Giới Hạn Pháp Lý Ngữ Nghĩa</span>
                </div>
                <p>
                  • Mô hình: <strong className="text-brand-text-primary print:text-black">YOLO11s</strong> (Class 0: person) | Checkpoint SHA-256: <code className="font-mono text-[10px] text-brand-text-primary print:text-black">{reportData.session.checkpointSha256?.slice(0, 16)}...</code>
                </p>
                <p>
                  • <strong>Cam kết tính trung thực ngữ nghĩa:</strong> Báo cáo ghi nhận số người nhìn thấy tức thời trong khung hình 2D từ góc camera cố định. Tuyệt đối không suy diễn sức chứa địa điểm, tỷ lệ lấp đầy, hay số người tổng thể khi chưa có hiệu chuẩn trắc đạc 3D.
                </p>
              </div>
            </div>
          )}

          {/* TAB 2: INTERACTIVE MULTI-ZONE COMPARISON VIEW */}
          {activeTab === 'comparison' && (
            <div className="space-y-6 max-w-4xl mx-auto">
              {/* Comparative SVG Trend Chart */}
              <div
                style={{ backgroundColor: '#141D2C' }}
                className="p-5 rounded-2xl border border-[#243346] space-y-4"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-brand-gold" />
                    <h3 className="font-bold text-sm text-brand-text-primary">
                      Đồ Thị Xu Hướng Biến Thiên Đa Vùng Theo Thời Gian
                    </h3>
                  </div>
                  <div className="flex items-center gap-3 text-xs">
                    {reportData.zoneSummaries.map((zs) => (
                      <span key={zs.zoneId} className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: zs.color }} />
                        <span className="text-brand-text-muted">{zs.name}</span>
                      </span>
                    ))}
                  </div>
                </div>

                {/* SVG Graph */}
                <div className="w-full overflow-x-auto">
                  <svg
                    viewBox={`0 0 ${svgWidth} ${svgHeight}`}
                    onMouseMove={(e) => {
                      const rect = e.currentTarget.getBoundingClientRect();
                      const relX = ((e.clientX - rect.left) / rect.width) * svgWidth;
                      const ratio = Math.max(0, Math.min(1, (relX - padding.left) / chartW));
                      const idx = Math.min(
                        reportData.timelineRows.length - 1,
                        Math.max(0, Math.round(ratio * (reportData.timelineRows.length - 1)))
                      );
                      setHoveredTrendIndex(idx);
                    }}
                    onMouseLeave={() => setHoveredTrendIndex(null)}
                    className="w-full h-auto select-none overflow-visible cursor-crosshair"
                  >
                    {/* Background gridlines */}
                    {[0, 0.25, 0.5, 0.75, 1].map((pct, i) => {
                      const y = padding.top + chartH * (1 - pct);
                      const val = Math.round(maxVal * pct);
                      return (
                        <g key={i}>
                          <line
                            x1={padding.left}
                            y1={y}
                            x2={padding.left + chartW}
                            y2={y}
                            stroke="#223043"
                            strokeDasharray="3 3"
                            strokeWidth="1"
                          />
                          <text
                            x={padding.left - 8}
                            y={y + 4}
                            textAnchor="end"
                            fontSize="9"
                            fill="#8A98A8"
                            fontFamily="monospace"
                          >
                            {val}
                          </text>
                        </g>
                      );
                    })}

                    {/* Time ticks */}
                    {[0, 0.25, 0.5, 0.75, 1].map((pct, i) => {
                      const x = padding.left + chartW * pct;
                      const t = duration * pct;
                      return (
                        <g key={i}>
                          <line
                            x1={x}
                            y1={padding.top + chartH}
                            x2={x}
                            y2={padding.top + chartH + 5}
                            stroke="#223043"
                          />
                          <text
                            x={x}
                            y={padding.top + chartH + 16}
                            textAnchor="middle"
                            fontSize="9"
                            fill="#8A98A8"
                            fontFamily="monospace"
                          >
                            {formatTime(t)}
                          </text>
                        </g>
                      );
                    })}

                    {/* Zone trend lines */}
                    {reportData.zoneSummaries.map((zs) => {
                      const points = reportData.timelineRows.map((row) => {
                        const x = padding.left + (row.time / duration) * chartW;
                        const count = row.zoneCounts[zs.zoneId] ?? 0;
                        const y = padding.top + chartH * (1 - count / maxVal);
                        return `${x},${y}`;
                      });

                      if (points.length < 2) return null;

                      return (
                        <polyline
                          key={zs.zoneId}
                          fill="none"
                          stroke={zs.color}
                          strokeWidth="2.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          points={points.join(' ')}
                        />
                      );
                    })}

                    {/* Hover cursor if applicable */}
                    {hoveredTrendIndex !== null && reportData.timelineRows[hoveredTrendIndex] && (
                      (() => {
                        const row = reportData.timelineRows[hoveredTrendIndex];
                        const x = padding.left + (row.time / duration) * chartW;
                        return (
                          <line
                            x1={x}
                            y1={padding.top}
                            x2={x}
                            y2={padding.top + chartH}
                            stroke="#E69F00"
                            strokeWidth="1.5"
                            strokeDasharray="4 2"
                          />
                        );
                      })()
                    )}
                  </svg>
                </div>
              </div>

              {/* Matrix of Analytics Details */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {reportData.zoneSummaries.map((zs) => (
                  <div
                    key={zs.zoneId}
                    style={{ backgroundColor: '#141D2C' }}
                    className="p-4 rounded-2xl border border-[#243346] space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="w-3.5 h-3.5 rounded-full" style={{ backgroundColor: zs.color }} />
                        <span className="font-bold text-sm text-brand-text-primary">{zs.name}</span>
                      </div>
                      <span className="font-mono text-xs font-bold text-brand-gold bg-brand-gold/10 px-2 py-0.5 rounded border border-brand-gold/30">
                        {zs.sharePct}% thị phần
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div style={{ backgroundColor: '#101622' }} className="p-2 rounded-lg border border-[#223043]">
                        <div className="text-[10px] text-brand-text-muted">Đỉnh quan sát</div>
                        <div className="font-mono font-bold text-sm text-brand-gold mt-0.5">{zs.maxCount}</div>
                      </div>
                      <div style={{ backgroundColor: '#101622' }} className="p-2 rounded-lg border border-[#223043]">
                        <div className="text-[10px] text-brand-text-muted">Trung bình</div>
                        <div className="font-mono font-bold text-sm text-cyan-400 mt-0.5">{zs.avgCount}</div>
                      </div>
                      <div style={{ backgroundColor: '#101622' }} className="p-2 rounded-lg border border-[#223043]">
                        <div className="text-[10px] text-brand-text-muted">Thấp nhất</div>
                        <div className="font-mono font-bold text-sm text-brand-text-muted mt-0.5">{zs.minCount}</div>
                      </div>
                    </div>

                    {onSeek && zs.peakTime > 0 && (
                      <button
                        type="button"
                        onClick={() => {
                          onSeek(zs.peakTime);
                          onClose();
                        }}
                        style={{ backgroundColor: '#182436' }}
                        className="w-full py-1.5 px-3 rounded-lg text-xs font-medium text-brand-gold hover:bg-brand-gold/15 border border-brand-gold/30 transition-colors text-center cursor-pointer"
                      >
                        Tua video tới thời điểm đỉnh ({formatTime(zs.peakTime)})
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </main>

        {/* --- 3. MODAL FOOTER ACTION BAR (Hidden in Print) --- */}
        <footer
          style={{ backgroundColor: '#161F2E' }}
          className="px-6 py-3 border-t border-[#243346] flex flex-wrap items-center justify-between gap-3 shrink-0 print:hidden"
        >
          <div className="flex items-center gap-2 text-[11px] text-brand-text-muted">
            <span>Bấm nút hoặc phím</span>
            <kbd className="px-1.5 py-0.5 rounded bg-black/40 border border-[#2D3F58] font-mono text-[10px] text-brand-gold font-bold">
              ESC
            </kbd>
            <span>để quay lại màn hình giám sát cũ</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleExcelExport}
              style={{ backgroundColor: '#182436' }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/10 font-medium text-xs transition-colors cursor-pointer"
              title="Tải file Excel đa trang tính (.xlsx)"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              <span>Xuất Excel (.xlsx)</span>
            </button>

            <button
              type="button"
              onClick={handlePrint}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-brand-gold hover:bg-brand-gold/90 text-brand-abyssal font-bold text-xs shadow transition-colors cursor-pointer"
              title="In trực tiếp hoặc Lưu dưới dạng PDF"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>In / Lưu PDF</span>
            </button>

            <button
              type="button"
              onClick={onClose}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-brand-gold/15 hover:bg-brand-gold/25 border border-brand-gold/40 text-brand-gold font-bold text-xs transition-colors cursor-pointer shadow-sm"
              title="Đóng báo cáo và quay lại màn hình giám sát cũ"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Quay lại màn cũ</span>
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
};
