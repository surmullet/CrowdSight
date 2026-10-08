import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Undo2,
  Redo2,
  Plus,
  Trash2,
  Save,
  Grid,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
} from 'lucide-react';
import { Banner } from '@/shared/ui/Banner';
import { useAuthStore } from '@/shared/state/authStore';

export interface EditableZone {
  zoneId: string;
  name: string;
  color: string;
  vertices: [number, number][]; // Pixel coordinates
}

interface ValidationFeedback {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

interface ZoneEditorProps {
  initialZoneSetName?: string;
  initialZones?: EditableZone[];
  imageWidth: number;
  imageHeight: number;
  sampleFrameUrl?: string;
  videoSrc?: string;
  onSave: (data: { name: string; zones: EditableZone[]; note: string }) => Promise<void>;
  onCancel: () => void;
  className?: string;
}

const PRESET_COLORS = [
  '#0072B2', // Deep Blue
  '#009E73', // Bluish Green
  '#D55E00', // Vermilion
  '#CC79A7', // Reddish Purple
  '#56B4E9', // Sky Blue
  '#E69F00', // Amber
];

export const ZoneEditor: React.FC<ZoneEditorProps> = ({
  initialZoneSetName = 'Tập vùng quan sát mới',
  initialZones = [],
  imageWidth,
  imageHeight,
  sampleFrameUrl,
  videoSrc,
  onSave,
  onCancel,
  className = '',
}) => {
  const { user } = useAuthStore();
  const isViewer = user?.role === 'VIEWER';
  const [zoneSetName, setZoneSetName] = useState(initialZoneSetName);
  const [versionNote, setVersionNote] = useState('Khởi tạo cấu hình ban đầu');
  const [imgError, setImgError] = useState(false);
  const [zones, setZones] = useState<EditableZone[]>(
    initialZones.length > 0
      ? initialZones
      : [
          {
            zoneId: 'zone-1',
            name: 'Khu vực A',
            color: PRESET_COLORS[0] ?? '#0072B2',
            vertices: [
              [Math.round(imageWidth * 0.2), Math.round(imageHeight * 0.3)],
              [Math.round(imageWidth * 0.5), Math.round(imageHeight * 0.3)],
              [Math.round(imageWidth * 0.45), Math.round(imageHeight * 0.7)],
              [Math.round(imageWidth * 0.15), Math.round(imageHeight * 0.7)],
            ],
          },
        ]
  );

  const [activeZoneId, setActiveZoneId] = useState<string>(zones[0]?.zoneId ?? '');
  const [snapToGrid, setSnapToGrid] = useState(false);
  const [gridSize] = useState(20);
  const [draggingVertex, setDraggingVertex] = useState<{ zoneId: string; index: number } | null>(null);
  const [history, setHistory] = useState<EditableZone[][]>([]);
  const [redoStack, setRedoStack] = useState<EditableZone[][]>([]);
  const [validation, setValidation] = useState<ValidationFeedback>({
    isValid: true,
    errors: [],
    warnings: [],
  });
  const [isSaving, setIsSaving] = useState(false);

  const svgRef = useRef<SVGSVGElement>(null);
  const dragOccurredRef = useRef(false);

  // Push to history before modifications
  const recordHistory = useCallback(() => {
    setHistory((prev) => [...prev.slice(-20), JSON.parse(JSON.stringify(zones))]);
    setRedoStack([]);
  }, [zones]);

  const handleUndo = () => {
    if (history.length === 0) return;
    const previous = history[history.length - 1];
    if (!previous) return;
    setRedoStack((prev) => [JSON.parse(JSON.stringify(zones)), ...prev]);
    setZones(previous);
    setHistory((prev) => prev.slice(0, -1));
  };

  const handleRedo = () => {
    if (redoStack.length === 0) return;
    const next = redoStack[0];
    if (!next) return;
    setHistory((prev) => [...prev, JSON.parse(JSON.stringify(zones))]);
    setZones(next);
    setRedoStack((prev) => prev.slice(1));
  };

  // Real-time client-side geometry validation
  useEffect(() => {
    const errors: string[] = [];
    const warnings: string[] = [];

    if (zones.length === 0) {
      errors.push('Tập vùng phải chứa ít nhất 1 zone.');
    }

    for (const z of zones) {
      if (z.vertices.length < 3) {
        errors.push(`Vùng "${z.name}" cần ít nhất 3 đỉnh để tạo thành polygon.`);
      }
      // Check boundaries
      for (const [x, y] of z.vertices) {
        if (x < 0 || x > imageWidth || y < 0 || y > imageHeight) {
          errors.push(`Vùng "${z.name}" có đỉnh nằm ngoài khung hình (${imageWidth}×${imageHeight}).`);
          break;
        }
      }
    }

    if (zones.length > 1) {
      warnings.push('Chú ý: Nếu các zone chồng lấn, người trong vùng chung sẽ được đếm vào cả hai zone.');
    }

    setValidation({
      isValid: errors.length === 0,
      errors,
      warnings,
    });
  }, [zones, imageWidth, imageHeight]);

  const getSvgCoordinatesFromClient = useCallback(
    (clientX: number, clientY: number): [number, number] => {
      const svg = svgRef.current;
      if (!svg) return [0, 0];
      const rect = svg.getBoundingClientRect();
      const scaleX = imageWidth / rect.width;
      const scaleY = imageHeight / rect.height;
      let px = (clientX - rect.left) * scaleX;
      let py = (clientY - rect.top) * scaleY;

      if (snapToGrid) {
        px = Math.round(px / gridSize) * gridSize;
        py = Math.round(py / gridSize) * gridSize;
      }

      px = Math.max(0, Math.min(imageWidth, Math.round(px)));
      py = Math.max(0, Math.min(imageHeight, Math.round(py)));

      return [px, py];
    },
    [gridSize, imageHeight, imageWidth, snapToGrid]
  );

  // Global window listeners for drag move and release
  useEffect(() => {
    if (!draggingVertex) return;

    const handleWindowMouseMove = (e: MouseEvent) => {
      dragOccurredRef.current = true;
      const [px, py] = getSvgCoordinatesFromClient(e.clientX, e.clientY);

      setZones((prev) =>
        prev.map((z) => {
          if (z.zoneId !== draggingVertex.zoneId) return z;
          const newVertices: [number, number][] = z.vertices.map((v, i) =>
            i === draggingVertex.index ? [px, py] : v
          );
          return { ...z, vertices: newVertices };
        })
      );
    };

    const handleWindowMouseUp = () => {
      setDraggingVertex(null);
      // Keep dragOccurredRef true briefly so click event doesn't trigger
      setTimeout(() => {
        dragOccurredRef.current = false;
      }, 80);
    };

    window.addEventListener('mousemove', handleWindowMouseMove);
    window.addEventListener('mouseup', handleWindowMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleWindowMouseMove);
      window.removeEventListener('mouseup', handleWindowMouseUp);
    };
  }, [draggingVertex, getSvgCoordinatesFromClient]);

  // Click on empty canvas: only adds points if the active zone has fewer than 3 vertices!
  const handleSvgClick = (e: React.MouseEvent) => {
    if (dragOccurredRef.current || draggingVertex) return;

    const activeZone = zones.find((z) => z.zoneId === activeZoneId);
    if (!activeZone) return;

    // Only allow clicking to add initial vertices when starting a new zone from scratch
    if (activeZone.vertices.length < 3) {
      const [px, py] = getSvgCoordinatesFromClient(e.clientX, e.clientY);
      recordHistory();
      setZones((prev) =>
        prev.map((z) =>
          z.zoneId === activeZoneId ? { ...z, vertices: [...z.vertices, [px, py]] } : z
        )
      );
    }
  };

  // Mousedown on an existing vertex: ONLY moves this vertex
  const handleVertexMouseDown = (
    e: React.MouseEvent,
    zoneId: string,
    index: number
  ) => {
    e.stopPropagation();
    e.preventDefault();
    recordHistory();
    setActiveZoneId(zoneId);
    setDraggingVertex({ zoneId, index });
    dragOccurredRef.current = true;
  };

  // Mousedown on an EDGE: inserts a new vertex between edgeIndex and (edgeIndex+1) and starts dragging it
  const handleEdgeMouseDown = (
    e: React.MouseEvent,
    zoneId: string,
    edgeIndex: number
  ) => {
    e.stopPropagation();
    e.preventDefault();
    recordHistory();
    setActiveZoneId(zoneId);

    const [px, py] = getSvgCoordinatesFromClient(e.clientX, e.clientY);

    const insertIndex = edgeIndex + 1;
    setZones((prev) =>
      prev.map((z) => {
        if (z.zoneId !== zoneId) return z;
        const newVertices = [...z.vertices];
        newVertices.splice(insertIndex, 0, [px, py]);
        return { ...z, vertices: newVertices };
      })
    );

    // Immediately drag the newly inserted vertex
    setDraggingVertex({ zoneId, index: insertIndex });
    dragOccurredRef.current = true;
  };

  const handleDeleteVertex = (zoneId: string, index: number, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    const targetZone = zones.find((z) => z.zoneId === zoneId);
    if (!targetZone || targetZone.vertices.length <= 3) {
      // Must maintain at least 3 vertices for a polygon
      return;
    }

    recordHistory();
    setZones((prev) =>
      prev.map((z) => {
        if (z.zoneId !== zoneId) return z;
        return { ...z, vertices: z.vertices.filter((_, i) => i !== index) };
      })
    );
  };

  const handleAddZone = () => {
    recordHistory();
    const newId = `zone-${Date.now()}`;
    const color = PRESET_COLORS[zones.length % PRESET_COLORS.length] ?? '#0072B2';
    const newZone: EditableZone = {
      zoneId: newId,
      name: `Khu vực ${String.fromCharCode(65 + zones.length)}`,
      color,
      vertices: [],
    };
    setZones((prev) => [...prev, newZone]);
    setActiveZoneId(newId);
  };

  const handleDeleteZone = (zoneId: string) => {
    recordHistory();
    const updated = zones.filter((z) => z.zoneId !== zoneId);
    setZones(updated);
    if (activeZoneId === zoneId && updated[0]) {
      setActiveZoneId(updated[0].zoneId);
    }
  };

  const handleSave = async () => {
    if (!validation.isValid) return;
    setIsSaving(true);
    try {
      await onSave({
        name: zoneSetName,
        zones,
        note: versionNote,
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className={`flex flex-col min-h-screen bg-brand-abyssal text-brand-text-primary ${className}`}>
      <Banner />

      {/* Header */}
      <header className="px-8 py-4 border-b border-brand-border bg-brand-surface/40 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="p-1.5 rounded text-brand-text-muted hover:text-brand-text-primary hover:bg-brand-border"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-base font-bold text-brand-text-primary">
              Trình soạn thảo tập vùng quan sát
            </h1>
            <p className="text-xs text-brand-text-muted">
              {isViewer
                ? 'Chế độ Khách xem: Đang ở trạng thái chỉ đọc (Read-only)'
                : 'Kéo đỉnh để đổi vị trí • Kéo cạnh để thêm đỉnh mới • Chuột phải để xóa đỉnh'}
            </p>
          </div>
        </div>

        {/* Action Toolbar */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleUndo}
            disabled={history.length === 0}
            className="p-1.5 rounded border border-brand-border bg-brand-surface text-brand-text-muted hover:text-brand-text-primary disabled:opacity-40"
            title="Hoàn tác (Undo)"
          >
            <Undo2 className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={handleRedo}
            disabled={redoStack.length === 0}
            className="p-1.5 rounded border border-brand-border bg-brand-surface text-brand-text-muted hover:text-brand-text-primary disabled:opacity-40"
            title="Làm lại (Redo)"
          >
            <Redo2 className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => setSnapToGrid(!snapToGrid)}
            className={`flex items-center gap-1 px-2.5 py-1.5 rounded text-xs border ${
              snapToGrid
                ? 'bg-brand-gold/15 text-brand-gold border-brand-gold/40'
                : 'bg-brand-surface text-brand-text-muted border-brand-border hover:text-brand-text-primary'
            }`}
          >
            <Grid className="w-3.5 h-3.5" />
            <span>Bám lưới (20px)</span>
          </button>

          <button
            type="button"
            onClick={handleSave}
            disabled={isViewer || !validation.isValid || isSaving}
            className={`flex items-center gap-1.5 px-4 py-1.5 font-semibold text-xs rounded-lg transition-colors shadow ${
              isViewer
                ? 'bg-brand-surface text-brand-text-muted/40 cursor-not-allowed border border-brand-border/60'
                : 'bg-brand-gold hover:bg-brand-gold/90 disabled:opacity-40 text-brand-abyssal cursor-pointer'
            }`}
            title={isViewer ? 'Khách xem không có quyền lưu chỉnh sửa vùng' : undefined}
          >
            <Save className="w-3.5 h-3.5" />
            <span>{isSaving ? 'Đang lưu...' : isViewer ? 'Chỉ xem (Không được lưu)' : 'Lưu phiên bản mới'}</span>
          </button>
        </div>
      </header>

      {/* Main Studio Area */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 p-6">
        {/* Left: SVG Canvas over Background Frame (8 cols) */}
        <div className="lg:col-span-8 flex flex-col gap-2">
          <div className="relative w-full aspect-video bg-black rounded-xl overflow-hidden border border-brand-border select-none shadow-xl">
            {/* Background Sample Image */}
            {sampleFrameUrl && !imgError && (
              <img
                src={sampleFrameUrl}
                alt="Khung hình tham chiếu để vẽ vùng"
                onError={() => setImgError(true)}
                className="absolute inset-0 w-full h-full object-contain pointer-events-none"
              />
            )}

            {/* Video element fallback: decodes and displays first frame directly from video stream/file */}
            {videoSrc && (
              <video
                src={videoSrc}
                crossOrigin="anonymous"
                preload="auto"
                muted
                playsInline
                onLoadedMetadata={(e) => {
                  const v = e.currentTarget;
                  v.currentTime = 0.1;
                }}
                className={`absolute inset-0 w-full h-full object-contain pointer-events-none ${
                  sampleFrameUrl && !imgError ? 'hidden' : ''
                }`}
              />
            )}

            {/* Interactive SVG Drawing Canvas */}
            <svg
              ref={svgRef}
              viewBox={`0 0 ${imageWidth} ${imageHeight}`}
              onClick={handleSvgClick}
              className="absolute inset-0 w-full h-full select-none"
            >
              {/* Optional Grid overlay */}
              {snapToGrid && (
                <defs>
                  <pattern id="gridPattern" width="40" height="40" patternUnits="userSpaceOnUse">
                    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#222D3E" strokeWidth="0.5" />
                  </pattern>
                </defs>
              )}
              {snapToGrid && <rect width={imageWidth} height={imageHeight} fill="url(#gridPattern)" />}

              {/* Draw Polygons for each zone */}
              {zones.map((zone) => {
                const isActive = zone.zoneId === activeZoneId;
                const pointsStr = zone.vertices.map((v) => `${v[0]},${v[1]}`).join(' ');
                const numVerts = zone.vertices.length;

                return (
                  <g key={zone.zoneId}>
                    {/* Filled Polygon */}
                    {numVerts >= 3 && (
                      <polygon
                        points={pointsStr}
                        fill={`${zone.color}26`}
                        stroke={zone.color}
                        strokeWidth={isActive ? '3' : '1.5'}
                        strokeDasharray={isActive ? undefined : '4,2'}
                        onClick={() => setActiveZoneId(zone.zoneId)}
                        className="cursor-pointer"
                      />
                    )}

                    {/* Interactive Edges: pure CSS group-hover highlight & midpoint "+" handle */}
                    {numVerts >= 2 &&
                      zone.vertices.map(([x1, y1], edgeIdx) => {
                        const nextIdx = (edgeIdx + 1) % numVerts;
                        if (numVerts === 2 && edgeIdx === 1) return null; // Incomplete line
                        const [x2, y2] = zone.vertices[nextIdx]!;
                        const midX = (x1 + x2) / 2;
                        const midY = (y1 + y2) / 2;

                        return (
                          <g key={`edge-${zone.zoneId}-${edgeIdx}`} className="group/edge cursor-copy">
                            {/* Fat invisible hit area */}
                            <line
                              x1={x1}
                              y1={y1}
                              x2={x2}
                              y2={y2}
                              stroke="transparent"
                              strokeWidth={16}
                              onMouseDown={(e) => handleEdgeMouseDown(e, zone.zoneId, edgeIdx)}
                            >
                              <title>Kéo cạnh này để tạo thêm đỉnh mới</title>
                            </line>

                            {/* Edge highlight on hover (pure CSS group-hover: no React re-render, no jitter) */}
                            {isActive && (
                              <>
                                <line
                                  x1={x1}
                                  y1={y1}
                                  x2={x2}
                                  y2={y2}
                                  stroke="#F5A623"
                                  strokeWidth={2.5}
                                  strokeDasharray="6,4"
                                  className="pointer-events-none opacity-0 group-hover/edge:opacity-100 transition-opacity duration-150"
                                />
                                {/* Midpoint "+" Handle */}
                                <g
                                  transform={`translate(${midX}, ${midY})`}
                                  className="pointer-events-none opacity-0 group-hover/edge:opacity-100 transition-opacity duration-150"
                                >
                                  <circle
                                    r={8}
                                    fill="#F5A623"
                                    stroke="#FFFFFF"
                                    strokeWidth={2}
                                    className="drop-shadow"
                                  />
                                  <line x1={-3.5} y1={0} x2={3.5} y2={0} stroke="#1A1F2C" strokeWidth={2} strokeLinecap="round" />
                                  <line x1={0} y1={-3.5} x2={0} y2={3.5} stroke="#1A1F2C" strokeWidth={2} strokeLinecap="round" />
                                </g>
                              </>
                            )}
                          </g>
                        );
                      })}

                    {/* Vertices Draggable Dots: Stable 14px hit target, NO hover:scale (prevents SVG boundary tremor) */}
                    {zone.vertices.map(([vx, vy], idx) => {
                      const isDraggingThis =
                        draggingVertex?.zoneId === zone.zoneId && draggingVertex?.index === idx;

                      return (
                        <g key={`v-grp-${zone.zoneId}-${idx}`} className="group/vertex cursor-move">
                          {/* Generous 14px radius hit area so cursor never drops off */}
                          <circle
                            cx={vx}
                            cy={vy}
                            r={14}
                            fill="transparent"
                            onMouseDown={(e) => handleVertexMouseDown(e, zone.zoneId, idx)}
                            onContextMenu={(e) => handleDeleteVertex(zone.zoneId, idx, e)}
                          >
                            <title>Kéo để di chuyển • Chuột phải để xóa đỉnh</title>
                          </circle>

                          {/* Crisp visible dot with smooth color transitions, no geometry transforms */}
                          <circle
                            cx={vx}
                            cy={vy}
                            r={isDraggingThis ? 9 : isActive ? 7.5 : 5}
                            fill={isDraggingThis ? '#F5A623' : isActive ? '#FFFFFF' : zone.color}
                            stroke={isDraggingThis ? '#FFFFFF' : zone.color}
                            strokeWidth={isDraggingThis ? 3 : 2}
                            className="pointer-events-none drop-shadow-md group-hover/vertex:fill-amber-400 group-hover/vertex:stroke-white transition-colors duration-150"
                          />
                        </g>
                      );
                    })}
                  </g>
                );
              })}
            </svg>
          </div>

          <div className="text-[11px] text-brand-text-muted flex justify-between px-1">
            <span>
              🎯 <strong className="text-brand-text-primary">Kéo đỉnh:</strong> Di chuyển đỉnh đó &bull;{' '}
              ➕ <strong className="text-brand-gold">Kéo cạnh:</strong> Tạo thêm đỉnh mới &bull;{' '}
              ❌ <strong className="text-red-400">Chuột phải đỉnh:</strong> Xóa đỉnh
            </span>
            <span>Độ phân giải tham chiếu: {imageWidth}×{imageHeight} px</span>
          </div>
        </div>

        {/* Right: Zones Inspector & Metadata (4 cols) */}
        <div className="lg:col-span-4 flex flex-col gap-4 text-xs">
          {/* Metadata: Name & Version Note */}
          <div className="p-4 bg-brand-surface border border-brand-border rounded-xl space-y-3">
            <div>
              <label className="text-[11px] font-medium text-brand-text-muted">Tên tập vùng</label>
              <input
                type="text"
                value={zoneSetName}
                onChange={(e) => setZoneSetName(e.target.value)}
                className="w-full mt-1 px-3 py-1.5 bg-brand-abyssal border border-brand-border rounded text-xs text-brand-text-primary focus:border-brand-gold outline-none"
              />
            </div>
            <div>
              <label className="text-[11px] font-medium text-brand-text-muted">Ghi chú phiên bản</label>
              <input
                type="text"
                value={versionNote}
                onChange={(e) => setVersionNote(e.target.value)}
                placeholder="Lý do điều chỉnh ranh giới..."
                className="w-full mt-1 px-3 py-1.5 bg-brand-abyssal border border-brand-border rounded text-xs text-brand-text-primary focus:border-brand-gold outline-none"
              />
            </div>
          </div>

          {/* Zones List & Management */}
          <div className="p-4 bg-brand-surface border border-brand-border rounded-xl space-y-3 flex-1 flex flex-col">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-brand-text-primary">
                Danh sách vùng ({zones.length})
              </span>
              {!isViewer && (
                <button
                  type="button"
                  onClick={handleAddZone}
                  className="flex items-center gap-1 text-xs text-brand-gold hover:underline cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Thêm zone</span>
                </button>
              )}
            </div>

            <div className="space-y-2 overflow-y-auto max-h-[280px] flex-1 pr-1">
              {zones.map((zone) => {
                const isActive = zone.zoneId === activeZoneId;
                return (
                  <div
                    key={zone.zoneId}
                    onClick={() => setActiveZoneId(zone.zoneId)}
                    className={`p-3 rounded-lg border cursor-pointer transition-all flex items-center justify-between ${
                      isActive
                        ? 'border-brand-gold bg-brand-gold/5 shadow-sm'
                        : 'border-brand-border bg-brand-abyssal/60 hover:border-brand-border/80'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <div
                        className="w-3.5 h-3.5 rounded-full border border-white/20 shrink-0"
                        style={{ backgroundColor: zone.color }}
                      />
                      <div>
                        <input
                          type="text"
                          value={zone.name}
                          onChange={(e) => {
                            const val = e.target.value;
                            setZones((prev) =>
                              prev.map((z) => (z.zoneId === zone.zoneId ? { ...z, name: val } : z))
                            );
                          }}
                          className="font-medium bg-transparent border-none text-brand-text-primary text-xs focus:ring-1 focus:ring-brand-gold rounded px-1 -ml-1 outline-none"
                        />
                        <div className="text-[10px] text-brand-text-muted">
                          {zone.vertices.length} đỉnh
                        </div>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteZone(zone.zoneId);
                      }}
                      className="text-brand-text-muted hover:text-red-400 p-1 rounded"
                      title="Xóa vùng này"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Real-time Validation Feedback Card */}
          <div className="p-4 bg-brand-surface border border-brand-border rounded-xl space-y-2">
            <div className="flex items-center gap-1.5 font-semibold text-xs">
              {validation.isValid ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span className="text-emerald-400">Hình học hợp lệ</span>
                </>
              ) : (
                <>
                  <AlertCircle className="w-4 h-4 text-red-400" />
                  <span className="text-red-400">Phát hiện lỗi hình học</span>
                </>
              )}
            </div>

            {validation.errors.length > 0 && (
              <ul className="text-[11px] text-red-300 space-y-1 list-disc list-inside">
                {validation.errors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            )}

            {validation.warnings.length > 0 && (
              <div className="pt-1 text-[11px] text-amber-300 flex items-start gap-1">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                <span>{validation.warnings[0]}</span>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};
