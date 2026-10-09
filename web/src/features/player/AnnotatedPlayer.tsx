import React, { useEffect, useRef, useState, useCallback } from 'react';
import type { CrowdFrameObservation } from '@/shared/types/domain';
import {
  computeLetterbox,
  normalizedToCanvasCoords,
  sourceBoxToCanvasCoords,
  type LetterboxRect,
} from '@/shared/geometry/overlayMath';
import { usePlaybackStore } from '@/shared/state/playbackStore';

interface ZoneOverlayDefinition {
  zone_id: string;
  name: string;
  color: string;
  vertices: [number, number][]; // Pixel coordinates in original image
}

interface AnnotatedPlayerProps {
  videoSrc: string;
  imageWidth: number;
  imageHeight: number;
  zones: ZoneOverlayDefinition[];
  observation: CrowdFrameObservation | null;
  heatmapUrl?: string | null;
  onTimeUpdate?: (time: number) => void;
  className?: string;
}

export const AnnotatedPlayer: React.FC<AnnotatedPlayerProps> = ({
  videoSrc,
  imageWidth,
  imageHeight,
  zones,
  observation,
  heatmapUrl,
  onTimeUpdate,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const heatmapImgRef = useRef<HTMLImageElement | null>(null);

  const {
    currentTime,
    isPlaying,
    playbackRate,
    showBoxes,
    showZones,
    showHeatmap,
    heatmapOpacity,
    minConfidence,
    setCurrentTime,
    setDuration,
    setIsPlaying,
  } = usePlaybackStore();

  const [letterbox, setLetterbox] = useState<LetterboxRect>({
    offsetX: 0,
    offsetY: 0,
    renderWidth: 0,
    renderHeight: 0,
    scale: 1,
  });

  // Preload heat map image when heatmapUrl changes
  useEffect(() => {
    if (!heatmapUrl) {
      heatmapImgRef.current = null;
      return;
    }
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.src = heatmapUrl;
    img.onload = () => {
      heatmapImgRef.current = img;
    };
  }, [heatmapUrl]);

  // Reload video element whenever videoSrc changes (e.g. re-upload or new session)
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.load();
    }
  }, [videoSrc]);

  // Sync seek/scrub from timeline and step controls to video element
  useEffect(() => {
    const video = videoRef.current;
    if (video && Math.abs(video.currentTime - currentTime) > 0.15) {
      video.currentTime = currentTime;
    }
  }, [currentTime]);

  // Sync playback play/pause state
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    if (isPlaying && video.paused) {
      video.play().catch(() => setIsPlaying(false));
    } else if (!isPlaying && !video.paused) {
      video.pause();
    }
  }, [isPlaying, setIsPlaying]);

  // Sync playback rate
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.playbackRate = playbackRate;
    }
  }, [playbackRate]);

  // Update letterbox bounds on container resize
  const updateGeometry = useCallback(() => {
    const container = containerRef.current;
    const video = videoRef.current;
    if (!container || !video) return;

    const vWidth = video.videoWidth || imageWidth;
    const vHeight = video.videoHeight || imageHeight;
    const cWidth = container.clientWidth;
    const cHeight = container.clientHeight;

    const lb = computeLetterbox(cWidth, cHeight, vWidth, vHeight);
    setLetterbox(lb);

    // Adjust canvas buffer to match devicePixelRatio
    const canvas = canvasRef.current;
    if (canvas) {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = cWidth * dpr;
      canvas.height = cHeight * dpr;
    }
  }, [imageWidth, imageHeight]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver(() => updateGeometry());
    observer.observe(container);
    return () => observer.disconnect();
  }, [updateGeometry]);

  // Render canvas layers
  const renderOverlay = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (letterbox.renderWidth <= 0 || letterbox.renderHeight <= 0) return;

    // 1. Heat map layer
    if (showHeatmap && heatmapImgRef.current) {
      ctx.save();
      ctx.globalAlpha = heatmapOpacity;
      const destX = letterbox.offsetX * dpr;
      const destY = letterbox.offsetY * dpr;
      const destW = letterbox.renderWidth * dpr;
      const destH = letterbox.renderHeight * dpr;
      ctx.drawImage(heatmapImgRef.current, destX, destY, destW, destH);
      ctx.restore();
    }

    // 2. Zone polygons layer
    if (showZones && zones.length > 0) {
      for (const zone of zones) {
        if (!zone.vertices || zone.vertices.length < 3) continue;

        ctx.save();
        ctx.beginPath();
        for (let i = 0; i < zone.vertices.length; i++) {
          const v = zone.vertices[i];
          if (!v) continue;
          const normX = v[0] / imageWidth;
          const normY = v[1] / imageHeight;
          const pt = normalizedToCanvasCoords(normX, normY, letterbox, dpr);
          if (i === 0) {
            ctx.moveTo(pt.canvasX, pt.canvasY);
          } else {
            ctx.lineTo(pt.canvasX, pt.canvasY);
          }
        }
        ctx.closePath();

        // Polygon Fill and Stroke
        ctx.fillStyle = `${zone.color}26`; // ~15% opacity
        ctx.fill();
        ctx.strokeStyle = zone.color;
        ctx.lineWidth = 2 * dpr;
        ctx.stroke();

        // Zone Name Label at first vertex
        const firstV = zone.vertices[0];
        if (firstV) {
          const pt = normalizedToCanvasCoords(firstV[0] / imageWidth, firstV[1] / imageHeight, letterbox, dpr);
          ctx.font = `${11 * dpr}px 'Plus Jakarta Sans', sans-serif`;
          ctx.fillStyle = zone.color;
          ctx.fillText(zone.name, pt.canvasX + 4 * dpr, pt.canvasY - 4 * dpr);
        }
        ctx.restore();
      }
    }

    // 3. Person detection boxes layer
    // Invariant: Boxes only rendered when frame is VALID or PARTIAL. Never on UNKNOWN or STALE!
    const isQualityUsable = observation && (observation.quality === 'VALID' || observation.quality === 'PARTIAL');

    if (showBoxes && isQualityUsable && observation.detections) {
      const video = videoRef.current;
      const naturalWidth = (video && video.videoWidth > 0) ? video.videoWidth : (observation.image_width || imageWidth || 1920);
      const naturalHeight = (video && video.videoHeight > 0) ? video.videoHeight : (observation.image_height || imageHeight || 1080);

      for (const det of observation.detections) {
        if (det.confidence !== undefined && det.confidence < minConfidence) continue;

        const box = sourceBoxToCanvasCoords(det.bbox_xyxy, naturalWidth, naturalHeight, letterbox, dpr);

        ctx.save();
        // Bounding box
        ctx.strokeStyle = '#E69F00'; // Amber Beacon
        ctx.lineWidth = 1.5 * dpr;
        ctx.strokeRect(box.x, box.y, box.width, box.height);

        // Corner accents
        const cornerLen = Math.min(8 * dpr, box.width / 4, box.height / 4);
        ctx.strokeStyle = '#FFFFFF';
        ctx.lineWidth = 2 * dpr;

        // Top-left
        ctx.beginPath();
        ctx.moveTo(box.x, box.y + cornerLen);
        ctx.lineTo(box.x, box.y);
        ctx.lineTo(box.x + cornerLen, box.y);
        ctx.stroke();

        // Bottom-centre anchor point dot
        const anchor = normalizedToCanvasCoords(det.x, det.y, letterbox, dpr);
        ctx.fillStyle = '#E69F00';
        ctx.beginPath();
        ctx.arc(anchor.canvasX, anchor.canvasY, 3 * dpr, 0, 2 * Math.PI);
        ctx.fill();

        // Optional track ID tag
        if (det.track_id !== null && det.track_id !== undefined) {
          ctx.font = `bold ${10 * dpr}px 'Plus Jakarta Sans', monospace`;
          ctx.fillStyle = '#E69F00';
          ctx.fillText(`#${det.track_id}`, box.x + 2 * dpr, box.y - 3 * dpr);
        }

        ctx.restore();
      }
    }
  }, [
    letterbox,
    showHeatmap,
    heatmapOpacity,
    showZones,
    zones,
    imageWidth,
    imageHeight,
    showBoxes,
    observation,
    minConfidence,
  ]);

  // Frame synchronization loop
  useEffect(() => {
    let animId: number;
    let isMounted = true;

    const syncLoop = () => {
      if (!isMounted) return;
      const video = videoRef.current;
      if (video && !video.paused) {
        setCurrentTime(video.currentTime);
        if (onTimeUpdate) {
          onTimeUpdate(video.currentTime);
        }
      }
      renderOverlay();
      animId = requestAnimationFrame(syncLoop);
    };

    animId = requestAnimationFrame(syncLoop);
    return () => {
      isMounted = false;
      cancelAnimationFrame(animId);
    };
  }, [renderOverlay, setCurrentTime, onTimeUpdate]);

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full min-h-[360px] bg-black rounded-lg overflow-hidden flex items-center justify-center select-none ${className}`}
    >
      <video
        key={videoSrc}
        ref={videoRef}
        src={videoSrc}
        playsInline
        preload="auto"
        onLoadedMetadata={(e) => {
          setDuration(e.currentTarget.duration);
          updateGeometry();
        }}
        onEnded={() => setIsPlaying(false)}
        className="w-full h-full object-contain pointer-events-none"
      />

      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none"
      />

      {/* Floating Confidence Filter Stats Badge */}
      {showBoxes && observation && observation.detections && observation.detections.length > 0 && (
        <div className="absolute bottom-3 left-3 px-2 py-1 rounded bg-black/60 backdrop-blur-sm border border-white/10 text-[11px] font-mono text-brand-text-muted flex items-center gap-1.5 pointer-events-none z-10">
          <span className="w-1.5 h-1.5 rounded-full bg-brand-gold animate-pulse" />
          <span>
            {observation.detections.filter((d) => (d.confidence ?? 1) >= minConfidence).length} / {observation.detections.length} boxes (Conf ≥ {Math.round(minConfidence * 100)}%)
          </span>
        </div>
      )}
    </div>
  );
};
