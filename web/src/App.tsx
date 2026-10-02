import React, { useState, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  Film,
  Plus,
  Layers,
  Cpu,
  FlaskConical,
  Languages,
} from 'lucide-react';
import { SessionLibrary, type SessionSummaryItem } from '@/features/sessions/SessionLibrary';
import { NewSessionWizard, type MediaCatalogItem, type ZoneSetSummary, type ModelProfileInfo } from '@/features/wizard/NewSessionWizard';
import { JobProgressView } from '@/features/jobs/JobProgressView';
import { ReviewWorkspace, type SessionMetadata } from '@/features/review/ReviewWorkspace';
import { ZoneEditor } from '@/features/zones/ZoneEditor';
import { ModelStatusPage } from '@/features/model/ModelStatusPage';
import { DevStatesPage } from '@/features/dev/DevStatesPage';
import { usePlaybackStore } from '@/shared/state/playbackStore';
import type { CrowdFrameObservation, ZoneReading, FrameQuality } from '@/shared/types/domain';
import { LanguageProvider, useLanguage } from '@/shared/i18n/LanguageContext';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

type AppView = 'sessions' | 'wizard' | 'progress' | 'review' | 'zones' | 'model' | 'dev-states';

function isPointInPolygon(point: [number, number], vs: [number, number][]): boolean {
  const x = point[0], y = point[1];
  let inside = false;
  for (let i = 0, j = vs.length - 1; i < vs.length; j = i++) {
    const p1 = vs[i];
    const p2 = vs[j];
    if (!p1 || !p2) continue;
    const xi = p1[0], yi = p1[1];
    const xj = p2[0], yj = p2[1];
    const intersect = ((yi > y) !== (yj > y)) && (x < ((xj - xi) * (y - yi)) / (yj - yi) + xi);
    if (intersect) inside = !inside;
  }
  return inside;
}

const MOCK_MEDIA_CATALOG: MediaCatalogItem[] = [
  {
    id: '5cc6461b-1cb0-4700-8305-b01c78780785',
    name: 'crowd6.mp4 (Video Vừa Tải Lên - AI Quét Thật)',
    duration: 25.12,
    fps: 25,
    width: 1280,
    height: 720,
    codec: 'h264',
    browserPlayable: true,
    videoSrc: '/crowd6.mp4',
  },
  {
    id: 'media-150',
    name: '150.mp4 (Video Vừa Tải Lên)',
    duration: 57.44,
    fps: 25,
    width: 1920,
    height: 1440,
    codec: 'h264',
    browserPlayable: true,
    videoSrc: '/150.mp4',
  },
  {
    id: 'media-sample-01',
    name: 'sample.mp4 (Video Phòng Giám Sát)',
    duration: 49.68,
    fps: 25,
    width: 1920,
    height: 1080,
    codec: 'h264',
    browserPlayable: true,
  },
  {
    id: 'media-plaza-01',
    name: 'plaza_pedestrian_cross_1080p.mp4',
    duration: 64.5,
    fps: 25,
    width: 1920,
    height: 1080,
    codec: 'h264',
    browserPlayable: true,
  },
  {
    id: 'media-station-02',
    name: 'metro_station_gate_north.mp4',
    duration: 120.0,
    fps: 30,
    width: 1920,
    height: 1080,
    codec: 'hevc',
    browserPlayable: false,
  },
];

const INITIAL_ZONE_SETS: ZoneSetSummary[] = [
  {
    id: 'a874db06-a600-4d64-803a-c4ce693f7925',
    name: 'Khu vực giám sát (crowd6.mp4)',
    version: 2,
    zoneCount: 2,
  },
  {
    id: '8658e0b9-f3b0-47ea-9a00-33fd947f6fd9',
    name: 'Khu vực Giám sát A & B (150.mp4)',
    version: 3,
    zoneCount: 2,
  },
];

const MOCK_MODEL_PROFILE: ModelProfileInfo = {
  profileId: 'crowd_best_local_v2',
  profileSha256: '83f5287f340ee77b4ba71f3014389146dfd2806283b9cf79427b3ecab6e7a2b2',
  checkpointSha256: '12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc',
  applicabilityStatus: 'EXPERIMENTAL_NO_APPROVAL',
  operationalAlertsAllowed: false,
};

const DEFAULT_SESSION: SessionSummaryItem = {
  id: 'session-150-real',
  sourceId: '150.mp4',
  mediaName: '150.mp4 (Video Vừa Tải Lên - AI Quét Thật)',
  duration: 57.44,
  status: 'COMPLETED',
  progress: 1.0,
  synthetic: false,
  createdAt: '2026-10-01 09:55:00',
  zoneSetName: 'Khu vực Giám sát A & B',
  qualityBreakdown: {
    validPct: 100,
    partialPct: 0,
    unknownPct: 0,
    stalePct: 0,
  },
};

const INITIAL_SESSIONS: SessionSummaryItem[] = [
  {
    id: 'session-crowd6-real',
    sourceId: '5cc6461b-1cb0-4700-8305-b01c78780785',
    mediaName: 'crowd6.mp4 (Video Vừa Tải Lên - AI Quét Thật)',
    duration: 25.12,
    status: 'COMPLETED',
    progress: 1.0,
    synthetic: false,
    createdAt: '2026-10-01 15:55:00',
    zoneSetName: 'Khu vực Giám sát A & B (crowd6)',
    videoSrc: '/crowd6.mp4',
    qualityBreakdown: {
      validPct: 100,
      partialPct: 0,
      unknownPct: 0,
      stalePct: 0,
    },
  },
  DEFAULT_SESSION,
  {
    id: 'session-yolo-real-01',
    sourceId: 'sample.mp4',
    mediaName: 'sample.mp4 (Quét AI YOLO11 Thật)',
    duration: 49.68,
    status: 'COMPLETED',
    progress: 1.0,
    synthetic: false,
    createdAt: '2026-10-01 09:25:00',
    zoneSetName: 'Khu vực Sảnh chính & Hành lang',
    qualityBreakdown: {
      validPct: 100,
      partialPct: 0,
      unknownPct: 0,
      stalePct: 0,
    },
  },
  {
    id: 'session-demo-01',
    sourceId: 'media-plaza-01',
    mediaName: 'plaza_pedestrian_cross_1080p.mp4 (Dữ liệu mẫu)',
    duration: 64.5,
    status: 'COMPLETED',
    progress: 1.0,
    synthetic: true,
    createdAt: '2026-09-30 08:30:00',
    zoneSetName: 'Khu vực quảng trường trung tâm',
    qualityBreakdown: {
      validPct: 82,
      partialPct: 12,
      unknownPct: 6,
      stalePct: 0,
    },
  },
];

const AppContent: React.FC = () => {
  const urlParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
  const initialView = (urlParams?.get('view') as AppView) || 'sessions';
  const initialSession = urlParams?.get('session') || INITIAL_SESSIONS[0]?.id || 'session-crowd6-real';

  const [currentView, setCurrentView] = useState<AppView>(initialView);
  const [selectedSessionId, setSelectedSessionId] = useState<string>(initialSession);
  const [useRealAI, setUseRealAI] = useState<boolean>(true);
  const [dataset150, setDataset150] = useState<any>(null);
  const [datasetSample, setDatasetSample] = useState<any>(null);
  const [datasetCrowd6, setDatasetCrowd6] = useState<any>(null);
  const { locale, toggleLocale, t } = useLanguage();
  const [sessions, setSessions] = useState<SessionSummaryItem[]>(INITIAL_SESSIONS);
  const [mediaCatalog, setMediaCatalog] = useState<MediaCatalogItem[]>(MOCK_MEDIA_CATALOG);
  const [zoneSets, setZoneSets] = useState<ZoneSetSummary[]>(INITIAL_ZONE_SETS);
  const [activeMediaForZoneEditor, setActiveMediaForZoneEditor] = useState<MediaCatalogItem | null>(null);
  const [sessionDatasetMap, setSessionDatasetMap] = useState<Record<string, any>>({});

  useEffect(() => {
    // 1. Fetch real sessions from SQLite backend
    fetch('/api/v1/sessions')
      .then((res) => (res.ok ? res.json() : []))
      .then((data: any[]) => {
        if (data && data.length > 0) {
          const backendSessions: SessionSummaryItem[] = data.map((item) => ({
            id: item.id,
            sourceId: item.media_asset_id,
            mediaName: item.media_name || 'Video phân tích',
            duration: item.duration_s || 25.12,
            status: item.status,
            progress: item.progress ?? 1.0,
            synthetic: item.synthetic,
            createdAt: item.created_at ? item.created_at.replace('T', ' ').slice(0, 19) : '',
            zoneSetName: item.zone_set_name || 'Khu vực giám sát',
            videoSrc: item.video_src,
            qualityBreakdown: {
              validPct: 100,
              partialPct: 0,
              unknownPct: 0,
              stalePct: 0,
            },
          }));
          setSessions((prev) => {
            const backendIds = new Set(backendSessions.map((b) => b.id));
            const keepPrev = prev.filter((p) => !backendIds.has(p.id));
            return [...backendSessions, ...keepPrev];
          });
        }
      })
      .catch((err) => console.log('Error fetching sessions:', err));

    // 2. Fetch real media assets from backend
    fetch('/api/v1/media')
      .then((res) => (res.ok ? res.json() : []))
      .then((data: any[]) => {
        if (data && data.length > 0) {
          const backendMedia: MediaCatalogItem[] = data.map((m) => ({
            id: m.id,
            name: m.display_name,
            duration: m.duration_s,
            fps: m.fps,
            width: m.width,
            height: m.height,
            codec: m.codec,
            browserPlayable: m.browser_playable,
            videoSrc: m.display_name === 'crowd6.mp4' ? '/crowd6.mp4' : m.display_name === '150.mp4' ? '/150.mp4' : `/api/v1/media/${m.id}/stream`,
          }));
          setMediaCatalog((prev) => {
            const backendIds = new Set(backendMedia.map((b) => b.id));
            const keepPrev = prev.filter((p) => !backendIds.has(p.id));
            return [...backendMedia, ...keepPrev];
          });
        }
      })
      .catch((err) => console.log('Error fetching media:', err));

    // 3. Fetch real zone-sets from backend
    fetch('/api/v1/zone-sets')
      .then((res) => (res.ok ? res.json() : []))
      .then((data: any[]) => {
        if (data && data.length > 0) {
          const backendZoneSets: ZoneSetSummary[] = data.map((zs) => {
            const latestVersion = zs.versions && zs.versions.length > 0
              ? zs.versions[zs.versions.length - 1]
              : null;
            return {
              id: latestVersion ? latestVersion.id : zs.id,
              name: zs.name,
              version: latestVersion ? latestVersion.version : 1,
              zoneCount: latestVersion?.polygon_data?.zones?.length || 2,
            };
          });
          setZoneSets((prev) => {
            const backendIds = new Set(backendZoneSets.map((b) => b.id));
            const keepPrev = prev.filter((p) => !backendIds.has(p.id));
            return [...backendZoneSets, ...keepPrev];
          });
        }
      })
      .catch((err) => console.log('Error fetching zone sets:', err));

    // Fallback fixtures
    fetch('/media_150_observations.json')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setDataset150(data);
      })
      .catch((err) => console.log('150 observations error:', err));

    fetch('/sample_real_observations.json')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setDatasetSample(data);
      })
      .catch((err) => console.log('sample observations error:', err));

    fetch('/media_crowd6_observations.json')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setDatasetCrowd6(data);
      })
      .catch((err) => console.log('crowd6 observations error:', err));
  }, []);

  const handleUploadMedia = async (file: File): Promise<MediaCatalogItem> => {
    const localBlobUrl = URL.createObjectURL(file);
    try {
      const res = await fetch(`/api/v1/media/upload?filename=${encodeURIComponent(file.name)}`, {
        method: 'POST',
        body: file,
      });
      if (res.ok) {
        const data = await res.json();
        const mediaItem: MediaCatalogItem = {
          id: data.id,
          name: data.display_name,
          duration: data.duration_s,
          fps: data.fps,
          width: data.width,
          height: data.height,
          codec: data.codec,
          browserPlayable: data.browser_playable,
          videoSrc: localBlobUrl,
        };
        setMediaCatalog((prev) => [mediaItem, ...prev]);
        return mediaItem;
      }
    } catch {
      // Fallback
    }

    const fallbackItem: MediaCatalogItem = {
      id: `media-upload-${Date.now().toString(36)}`,
      name: file.name,
      duration: 60.0,
      fps: 25,
      width: 1920,
      height: 1080,
      codec: 'h264',
      browserPlayable: true,
      videoSrc: localBlobUrl,
    };
    setMediaCatalog((prev) => [fallbackItem, ...prev]);
    return fallbackItem;
  };

  useEffect(() => {
    if (window.location.pathname === '/dev/states') {
      setCurrentView('dev-states');
    }
  }, []);

  const handleSelectSession = (id: string) => {
    setSelectedSessionId(id);
    setCurrentView('review');
  };

  const handleDeleteSession = async (id: string) => {
    try {
      await fetch(`/api/v1/sessions/${id}`, { method: 'DELETE' });
    } catch {
      // Ignore
    }
    setSessions((prev) => prev.filter((s) => s.id !== id));
  };

  const handleStartSession = async (params: {
    mediaId: string;
    zoneSetId: string;
    zoneSetVersion: number;
    frameStride: number;
    useSynthetic: boolean;
  }) => {
    try {
      const res = await fetch('/api/v1/sessions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          media_asset_id: params.mediaId,
          zone_set_version_id: params.zoneSetId,
          options: {
            enable_tracker: true,
            frame_stride: params.frameStride || 1,
          },
          use_synthetic: params.useSynthetic,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Khởi tạo phiên thất bại: ${res.statusText}`);
      }

      const created = await res.json();
      const newSession: SessionSummaryItem = {
        id: created.id,
        sourceId: created.media_asset_id,
        mediaName: created.media_name || 'Video phân tích',
        duration: created.duration_s || 25.12,
        status: created.status,
        progress: created.progress || 0.0,
        synthetic: created.synthetic,
        createdAt: created.created_at ? created.created_at.replace('T', ' ').slice(0, 19) : new Date().toISOString(),
        zoneSetName: created.zone_set_name || 'Khu vực giám sát',
        videoSrc: created.video_src,
        qualityBreakdown: {
          validPct: 100,
          partialPct: 0,
          unknownPct: 0,
          stalePct: 0,
        },
      };

      setSessions((prev) => [newSession, ...prev.filter((s) => s.id !== created.id)]);
      setSelectedSessionId(created.id);
      setCurrentView('progress');
    } catch (err) {
      console.error('Failed to create session:', err);
      throw err;
    }
  };

  // Load dataset for selected session if not already in memory
  useEffect(() => {
    if (!selectedSessionId) return;
    if (sessionDatasetMap[selectedSessionId]) return;
    if (
      selectedSessionId === 'session-crowd6-real' ||
      selectedSessionId === 'session-150-real' ||
      selectedSessionId === 'session-yolo-real-01' ||
      selectedSessionId === 'session-demo-01'
    ) {
      return;
    }

    fetch(`/api/v1/sessions/${selectedSessionId}/dataset`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) {
          setSessionDatasetMap((prev) => ({ ...prev, [selectedSessionId]: data }));
        }
      })
      .catch((err) => console.log('Dataset fetch error:', err));
  }, [selectedSessionId, sessionDatasetMap]);

  const { currentTime } = usePlaybackStore();

  const currentSession: SessionSummaryItem =
    sessions.find((s) => s.id === selectedSessionId) ?? sessions[0] ?? DEFAULT_SESSION;

  const sessionNameLower = (currentSession?.mediaName || '').toLowerCase();
  const sessionSourceLower = (currentSession?.sourceId || '').toLowerCase();

  const isCrowd6 = sessionNameLower.includes('crowd6') || sessionSourceLower.includes('crowd6');
  const is150 = !isCrowd6 && (sessionNameLower.includes('150') || sessionSourceLower.includes('150') || currentSession?.id === 'session-150-real');
  const isSample = !isCrowd6 && !is150 && (sessionNameLower.includes('sample') || sessionSourceLower.includes('sample') || currentSession?.id === 'session-yolo-real-01');

  const isSynthetic = Boolean(currentSession?.synthetic) || (!useRealAI && !is150 && !isSample && !isCrowd6);

  // Pick dataset based on session: prefer real session dataset from backend if available
  const loadedSessionDataset = sessionDatasetMap[currentSession?.id];
  const activeDataset = loadedSessionDataset || (
    isCrowd6
      ? datasetCrowd6
      : is150
        ? dataset150
        : isSample
          ? datasetSample
          : useRealAI
            ? (datasetCrowd6 || dataset150 || datasetSample)
            : null
  );

  const datasetFps = activeDataset?.metadata?.fps || 25;
  const datasetTotalFrames = activeDataset?.metadata?.totalFrames || activeDataset?.frames?.length || (isCrowd6 ? 628 : is150 ? 1436 : 1242);

  const currentFrameIdx = Math.min(
    Math.max(0, Math.round(currentTime * datasetFps)),
    datasetTotalFrames - 1
  );

  const realFrameObs = activeDataset?.frames ? activeDataset.frames[currentFrameIdx] : null;

  const activeQuality: FrameQuality = (!isSynthetic && realFrameObs)
    ? (realFrameObs.quality || 'VALID')
    : currentTime >= 40 && currentTime <= 55
      ? 'PARTIAL'
      : 'VALID';

  const baseCountNorth = Math.max(3, Math.round(14 + Math.sin(currentTime / 4) * 4));

  // Determine videoSrc accurately
  const matchedMedia = mediaCatalog.find(
    (m) => m.id === currentSession.sourceId || currentSession.mediaName.includes(m.name)
  );

  let videoSrc = currentSession.videoSrc || matchedMedia?.videoSrc;
  if (!videoSrc) {
    if (isCrowd6) {
      videoSrc = '/crowd6.mp4';
    } else if (is150) {
      videoSrc = '/150.mp4';
    } else if (isSample) {
      videoSrc = '/sample.mp4';
    } else if (currentSession.sourceId && !currentSession.sourceId.startsWith('session-')) {
      videoSrc = `/api/v1/media/${currentSession.sourceId}/stream`;
    } else {
      videoSrc = '/crowd6.mp4';
    }
  }

  const activeObservation: CrowdFrameObservation = (realFrameObs)
    ? {
        source_id: activeDataset?.metadata?.sourceId || currentSession.sourceId,
        session_id: currentSession?.id || selectedSessionId,
        model_profile_id: activeDataset?.metadata?.model || 'models/best.pt',
        model_profile_sha256: 'crowd_best_local_v2',
        checkpoint_sha256: 'best.pt',
        frame_index: realFrameObs.frame_index ?? currentFrameIdx,
        media_time_s: realFrameObs.media_time_s ?? +(currentFrameIdx / datasetFps).toFixed(2),
        image_width: activeDataset?.metadata?.width || (isCrowd6 ? 1280 : 1920),
        image_height: activeDataset?.metadata?.height || (isCrowd6 ? 720 : is150 ? 1440 : 1080),
        observation_valid: true,
        registration_valid: false,
        fully_observed_zones: activeDataset?.zones
          ? activeDataset.zones.map((z: any) => z.zone_id)
          : ['zone-a', 'zone-b'],
        confidence_semantics: 'RAW_MODEL_SCORE',
        quality: activeQuality,
        detections: realFrameObs.detections || [],
      }
    : {
        source_id: currentSession?.sourceId || (isCrowd6 ? 'crowd6.mp4' : is150 ? '150.mp4' : 'media-plaza-01'),
        session_id: currentSession?.id || selectedSessionId,
        model_profile_id: 'crowd_best_local_v2',
        model_profile_sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        checkpoint_sha256: '12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc',
        frame_index: Math.round(currentTime * 25),
        media_time_s: +currentTime.toFixed(2),
        image_width: matchedMedia?.width || (isCrowd6 ? 1280 : 1920),
        image_height: matchedMedia?.height || (isCrowd6 ? 720 : 1080),
        observation_valid: true,
        registration_valid: false,
        fully_observed_zones: ['zone-north', 'zone-south'],
        confidence_semantics: 'RAW_MODEL_SCORE',
        quality: activeQuality,
        detections: [
          { track_id: 101, x: 0.28, y: 0.42, confidence: 0.92, bbox_xyxy: [510, 390, 560, 480] },
          { track_id: 102, x: 0.35, y: 0.48, confidence: 0.89, bbox_xyxy: [640, 450, 700, 560] },
          { track_id: 103, x: 0.41, y: 0.38, confidence: 0.94, bbox_xyxy: [760, 360, 810, 440] },
          { track_id: 104, x: 0.22, y: 0.52, confidence: 0.86, bbox_xyxy: [390, 490, 450, 600] },
          { track_id: 105, x: 0.38, y: 0.58, confidence: 0.91, bbox_xyxy: [700, 550, 770, 680] },
          { track_id: 106, x: 0.31, y: 0.33, confidence: 0.88, bbox_xyxy: [570, 320, 620, 400] },
          { track_id: 107, x: 0.25, y: 0.40, confidence: 0.90, bbox_xyxy: [460, 380, 510, 470] },
          { track_id: 108, x: 0.44, y: 0.45, confidence: 0.87, bbox_xyxy: [820, 430, 880, 530] },
        ],
      };

  const activeReadings: ZoneReading[] = (realFrameObs?.zone_readings && realFrameObs.zone_readings.length > 0)
    ? realFrameObs.zone_readings.map((zr: any) => ({
        status: (zr.status === 'NOT_FULLY_OBSERVED' || zr.status === 'UNKNOWN' ? zr.status : 'COUNTED') as ZoneReading['status'],
        count: zr.count ?? 0,
        zoneId: zr.zoneId || zr.zone_id,
        zoneName: zr.zoneName || zr.name,
      }))
    : (activeDataset?.zones && realFrameObs)
      ? activeDataset.zones.map((z: any) => {
          const count = (realFrameObs.detections || []).filter((d: any) => {
            const px = d.bbox_xyxy ? (d.bbox_xyxy[0] + d.bbox_xyxy[2]) / 2 : d.x * (activeDataset.metadata?.width || (isCrowd6 ? 1280 : 1920));
            const py = d.bbox_xyxy ? d.bbox_xyxy[3] : d.y * (activeDataset.metadata?.height || (isCrowd6 ? 720 : 1440));
            return isPointInPolygon([px, py], z.vertices);
          }).length;
          return {
            status: 'COUNTED' as const,
            count,
            zoneId: z.zone_id,
            zoneName: z.name,
          };
        })
      : [
          {
            status: 'COUNTED',
            count: baseCountNorth,
            zoneId: 'zone-north',
            zoneName: 'Khu vực Bắc (Quảng trường)',
          },
          {
            status: 'COUNTED',
            count: 0,
            zoneId: 'zone-south',
            zoneName: 'Khu vực Nam (Lối vào)',
          },
        ];

  const handleExportCsv = () => {
    let rows = 'media_time_s,frame_index,zone_id,zone_name,visible_count,quality\n';
    activeReadings.forEach((r) => {
      const count = r.status === 'COUNTED' ? r.count : 0;
      rows += `${currentTime.toFixed(2)},${currentFrameIdx},${r.zoneId},${r.zoneName},${count},${activeQuality}\n`;
    });
    const encodedUri = encodeURI('data:text/csv;charset=utf-8,' + rows);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `crowdsight_${currentSession.id}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleExportJsonl = () => {
    const jsonlContent =
      'data:application/json;charset=utf-8,' +
      encodeURIComponent(JSON.stringify(activeObservation) + '\n');
    const link = document.createElement('a');
    link.setAttribute('href', jsonlContent);
    link.setAttribute('download', `crowdsight_${currentSession.id}_v1.jsonl`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const sampleReviewSession: SessionMetadata = {
    sessionId: currentSession.id,
    sourceId: currentSession.sourceId,
    mediaName: currentSession.mediaName,
    duration: activeDataset?.metadata?.duration || currentSession.duration || (isCrowd6 ? 25.12 : is150 ? 57.44 : 49.68),
    imageWidth: activeDataset?.metadata?.width || (isCrowd6 ? 1280 : 1920),
    imageHeight: activeDataset?.metadata?.height || (isCrowd6 ? 720 : (is150 ? 1440 : 1080)),
    synthetic: Boolean(currentSession.synthetic),
    modelProfileId: activeDataset?.metadata?.model || 'models/best.pt',
    modelProfileSha256: 'crowd_best_local_v2',
    checkpointSha256: 'best.pt',
    videoSrc: videoSrc,
    heatmapUrl: `/api/v1/sessions/${currentSession.id}/heatmap`,
  };

  const sampleZones = activeDataset?.zones || (isCrowd6
    ? [
        {
          zone_id: 'zone-a',
          name: 'Khu vực A (crowd6)',
          color: '#0072B2',
          vertices: [[100, 150], [600, 150], [550, 680], [80, 680]],
        },
        {
          zone_id: 'zone-b',
          name: 'Khu vực B (crowd6)',
          color: '#009E73',
          vertices: [[650, 150], [1200, 150], [1150, 680], [620, 680]],
        },
      ]
    : [
        {
          zone_id: 'zone-north',
          name: 'Khu vực Bắc (Quảng trường)',
          color: '#0072B2',
          vertices: [
            [300, 200] as [number, number],
            [900, 200] as [number, number],
            [850, 700] as [number, number],
            [250, 700] as [number, number],
          ],
        },
        {
          zone_id: 'zone-south',
          name: 'Khu vực Nam (Lối vào)',
          color: '#009E73',
          vertices: [
            [1000, 300] as [number, number],
            [1600, 300] as [number, number],
            [1550, 800] as [number, number],
            [950, 800] as [number, number],
          ],
        },
      ]);


  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-brand-abyssal text-brand-text-primary flex flex-col font-sans">
        {/* Navigation Bar */}
        <nav className="h-12 bg-brand-deck border-b border-brand-border px-6 flex items-center justify-between z-40 select-none">
          <div className="flex items-center gap-6">
            {/* Logo */}
            <button
              type="button"
              onClick={() => setCurrentView('sessions')}
              className="flex items-center gap-2 group cursor-pointer focus-visible:outline-none"
            >
              <div className="w-5 h-5 rounded bg-brand-gold flex items-center justify-center text-brand-abyssal font-bold text-xs shadow">
                C
              </div>
              <div className="flex items-baseline gap-1.5">
                <span className="font-bold text-sm tracking-tight text-brand-text-primary group-hover:text-brand-gold transition-colors">
                  CrowdSight
                </span>
                <span className="text-[10px] text-brand-text-muted hidden sm:inline">
                  {t.appSubtitle}
                </span>
              </div>
            </button>

            {/* Navigation Tabs */}
            <div className="flex items-center gap-1 text-xs">
              <button
                type="button"
                onClick={() => setCurrentView('sessions')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded transition-colors ${
                  currentView === 'sessions'
                    ? 'bg-brand-surface text-brand-gold font-medium'
                    : 'text-brand-text-muted hover:text-brand-text-primary'
                }`}
              >
                <Film className="w-3.5 h-3.5" />
                <span>{t.nav.sessions}</span>
              </button>

              <button
                type="button"
                onClick={() => setCurrentView('wizard')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded transition-colors ${
                  currentView === 'wizard'
                    ? 'bg-brand-surface text-brand-gold font-medium'
                    : 'text-brand-text-muted hover:text-brand-text-primary'
                }`}
              >
                <Plus className="w-3.5 h-3.5" />
                <span>{t.nav.wizard}</span>
              </button>

              <button
                type="button"
                onClick={() => setCurrentView('zones')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded transition-colors ${
                  currentView === 'zones'
                    ? 'bg-brand-surface text-brand-gold font-medium'
                    : 'text-brand-text-muted hover:text-brand-text-primary'
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                <span>{t.nav.zones}</span>
              </button>

              <button
                type="button"
                onClick={() => setCurrentView('model')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded transition-colors ${
                  currentView === 'model'
                    ? 'bg-brand-surface text-brand-gold font-medium'
                    : 'text-brand-text-muted hover:text-brand-text-primary'
                }`}
              >
                <Cpu className="w-3.5 h-3.5" />
                <span>{t.nav.model}</span>
              </button>

              <button
                type="button"
                onClick={() => setCurrentView('dev-states')}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded transition-colors ${
                  currentView === 'dev-states'
                    ? 'bg-brand-surface text-brand-gold font-medium'
                    : 'text-brand-text-muted hover:text-brand-text-primary'
                }`}
                title="Bàn kiểm thử trạng thái dữ liệu (/dev/states)"
              >
                <FlaskConical className="w-3.5 h-3.5 text-purple-400" />
                <span>/dev/states</span>
              </button>
            </div>
          </div>

          {/* Right utility items */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={toggleLocale}
              className="flex items-center gap-1 px-2.5 py-1 rounded text-xs text-brand-text-muted hover:text-brand-text-primary hover:bg-brand-surface border border-brand-border/50 hover:border-brand-gold/50 transition-colors cursor-pointer"
              title={t.nav.switchLanguage}
            >
              <Languages className="w-3.5 h-3.5 text-brand-gold" />
              <span className="font-mono text-[10px] uppercase font-bold text-brand-text-primary">{locale}</span>
            </button>
          </div>
        </nav>

        {/* View Switcher */}
        <div className="flex-1 flex flex-col">
          {currentView === 'sessions' && (
            <SessionLibrary
              sessions={sessions}
              onSelectSession={handleSelectSession}
              onNewSession={() => setCurrentView('wizard')}
              onDeleteSession={handleDeleteSession}
            />
          )}

          {currentView === 'wizard' && (
            <NewSessionWizard
              mediaCatalog={mediaCatalog}
              zoneSets={zoneSets}
              modelProfile={MOCK_MODEL_PROFILE}
              onCreateZoneSet={(mediaId) => {
                const found = mediaCatalog.find((m) => m.id === mediaId) || mediaCatalog[0];
                setActiveMediaForZoneEditor(found || null);
                setCurrentView('zones');
              }}
              onUploadMedia={handleUploadMedia}
              onSubmit={handleStartSession}
              onCancel={() => setCurrentView('sessions')}
            />
          )}

          {currentView === 'progress' && (
            <JobProgressView
              sessionId={selectedSessionId}
              initialData={{
                sessionId: selectedSessionId,
                mediaName: currentSession?.mediaName || '150.mp4',
                status: currentSession?.status || 'RUNNING',
                progress: currentSession?.progress || 0.1,
                currentFrame: Math.round((currentSession?.progress || 0.1) * (currentSession?.duration || 57) * 25),
                totalFrames: Math.round((currentSession?.duration || 57) * 25),
                fps: 25,
                etaSeconds: 2,
                qualityCounts: {
                  valid: 1400,
                  partial: 0,
                  unknown: 0,
                  stale: 0,
                },
                synthetic: currentSession?.synthetic,
              }}
              onComplete={() => {
                setSessions((prev) =>
                  prev.map((s) => (s.id === selectedSessionId ? { ...s, status: 'COMPLETED', progress: 1.0 } : s))
                );
                setCurrentView('review');
              }}
              onOpenPartialResults={() => {
                setSessions((prev) =>
                  prev.map((s) => (s.id === selectedSessionId ? { ...s, status: 'COMPLETED', progress: 1.0 } : s))
                );
                setCurrentView('review');
              }}
              onBackToLibrary={() => setCurrentView('sessions')}
            />
          )}

          {currentView === 'review' && (
            <ReviewWorkspace
              session={sampleReviewSession}
              zones={sampleZones}
              activeObservation={activeObservation}
              activeReadings={activeReadings}
              qualityIntervals={[
                { startTime: 0, endTime: 40, quality: 'VALID' },
                { startTime: 40, endTime: 55, quality: 'PARTIAL' },
                { startTime: 55, endTime: sampleReviewSession.duration, quality: 'VALID' },
              ]}
              zoneTrends={
                is150
                  ? [
                      {
                        zoneId: 'zone-a',
                        name: 'Khu vực Giám sát A (Bên trái)',
                        color: '#0072B2',
                        points: [
                          { time: 0, count: 0 },
                          { time: 10, count: 1 },
                          { time: 20, count: 1 },
                          { time: 30, count: 1 },
                          { time: 40, count: 1 },
                          { time: 50, count: 1 },
                          { time: 57, count: 1 },
                        ],
                      },
                      {
                        zoneId: 'zone-b',
                        name: 'Khu vực Giám sát B (Bên phải)',
                        color: '#009E73',
                        points: [
                          { time: 0, count: 0 },
                          { time: 10, count: 0 },
                          { time: 20, count: 0 },
                          { time: 30, count: 0 },
                          { time: 40, count: 0 },
                          { time: 50, count: 0 },
                          { time: 57, count: 0 },
                        ],
                      },
                    ]
                  : [
                      {
                        zoneId: 'zone-north',
                        name: 'Khu vực Bắc (Quảng trường)',
                        color: '#0072B2',
                        points: [
                          { time: 0, count: 5 },
                          { time: 10, count: 12 },
                          { time: 20, count: 18 },
                          { time: 30, count: 14 },
                          { time: 40, count: null },
                          { time: 50, count: null },
                          { time: 60, count: 11 },
                        ],
                      },
                    ]
              }
              peaks={
                is150
                  ? [{ time: 15, count: 1, zoneId: 'zone-a', label: '1 người trong Khu vực A' }]
                  : [{ time: 20, count: 18, zoneId: 'zone-north', label: 'Đỉnh lúc 00:20' }]
              }
              initialNotes={
                is150
                  ? [{ id: 'n1', time: 5, text: 'Phát hiện đối tượng di chuyển trong khu vực giám sát A.' }]
                  : [{ id: 'n1', time: 10, text: 'Bắt đầu có nhóm người di chuyển từ cổng vào.' }]
              }
              onExportCsv={handleExportCsv}
              onExportJsonl={handleExportJsonl}
              useRealAI={useRealAI}
              onToggleRealAI={() => setUseRealAI((prev) => !prev)}
              onEditZones={() => {
                const found = mediaCatalog.find((m) => m.id === currentSession.sourceId || currentSession.mediaName.includes(m.name)) || mediaCatalog[0];
                setActiveMediaForZoneEditor(found || null);
                setCurrentView('zones');
              }}
            />
          )}

          {currentView === 'zones' && (() => {
            const targetMedia = activeMediaForZoneEditor || mediaCatalog.find((m) => m.id === currentSession?.sourceId || currentSession?.mediaName?.includes(m.name)) || mediaCatalog[0];
            const targetName = targetMedia?.name?.toLowerCase() || '';
            const isTarget150 = targetName.includes('150');
            const isTargetSample = targetName.includes('sample');
            const isTargetRealPeople = targetName.includes('real_people');

            const resolvedFrameUrl = isTarget150
              ? '/media_150_frame.png'
              : isTargetSample
                ? '/sample-frame.png'
                : isTargetRealPeople
                  ? '/real_people_frame.png'
                  : targetMedia?.id && !targetMedia.id.startsWith('media-upload')
                    ? `/api/v1/media/${targetMedia.id}/frame?frame_index=0`
                    : undefined;

            const resolvedVideoSrc = targetMedia?.videoSrc || (
              isTarget150
                ? '/150.mp4'
                : isTargetSample
                  ? '/sample.mp4'
                  : isTargetRealPeople
                    ? '/real_people.mp4'
                    : targetMedia?.id && !targetMedia.id.startsWith('media-upload')
                      ? `/api/v1/media/${targetMedia.id}/stream`
                      : '/150.mp4'
            );

            const width = targetMedia?.width || 1920;
            const height = targetMedia?.height || (isTarget150 ? 1440 : 1080);

            return (
              <ZoneEditor
                key={`zone-editor-${targetMedia?.id || currentSession.id}-${sampleZones.length}`}
                initialZoneSetName={targetMedia?.name ? `Khu vực giám sát (${targetMedia.name.split(' ')[0]})` : (currentSession.zoneSetName || 'Khu vực quan sát')}
                initialZones={sampleZones.map((z: any) => ({
                  zoneId: z.zone_id,
                  name: z.name,
                  color: z.color,
                  vertices: z.vertices,
                }))}
                imageWidth={width}
                imageHeight={height}
                sampleFrameUrl={resolvedFrameUrl}
                videoSrc={resolvedVideoSrc}
                onSave={async (data) => {
                  const updatedZones = data.zones.map((z) => ({
                    zone_id: z.zoneId,
                    name: z.name,
                    color: z.color,
                    vertices: z.vertices,
                  }));
                  if (isTarget150) {
                    setDataset150((prev: any) => (prev ? { ...prev, zones: updatedZones } : prev));
                  } else {
                    setDatasetSample((prev: any) => (prev ? { ...prev, zones: updatedZones } : prev));
                  }

                  // Persist new zone set version to SQLite backend database (data/crowdsight.db)
                  try {
                    const zoneSetId = isTarget150 ? 'zones-150-real' : `zones-${targetMedia?.id || 'custom'}`;
                    const payload = {
                      image_width: width,
                      image_height: height,
                      zones: data.zones.map((z) => ({
                        zone_id: z.zoneId,
                        name: z.name,
                        vertices: z.vertices,
                        blind_regions: [],
                      })),
                    };

                    const res = await fetch(`/api/v1/zone-sets/${zoneSetId}/versions`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify(payload),
                    });
                    if (res.status === 404) {
                      await fetch('/api/v1/zone-sets', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                          id: zoneSetId,
                          name: data.name || (isTarget150 ? 'Khu vực Giám sát A & B' : 'Khu vực quan sát'),
                          ...payload,
                        }),
                      });
                    }
                  } catch (err) {
                    console.warn('Could not persist zone set to backend database:', err);
                  }

                  if (activeMediaForZoneEditor) {
                    setCurrentView('wizard');
                  } else {
                    setCurrentView('review');
                  }
                }}
                onCancel={() => {
                  if (activeMediaForZoneEditor) {
                    setCurrentView('wizard');
                  } else {
                    setCurrentView('review');
                  }
                }}
              />
            );
          })()}

          {currentView === 'model' && (
            <ModelStatusPage
              modelProfileId={MOCK_MODEL_PROFILE.profileId}
              modelProfileSha256={MOCK_MODEL_PROFILE.profileSha256}
              checkpointSha256={MOCK_MODEL_PROFILE.checkpointSha256}
              applicabilityStatus={MOCK_MODEL_PROFILE.applicabilityStatus}
              operationalAlertsAllowed={MOCK_MODEL_PROFILE.operationalAlertsAllowed}
            />
          )}

          {currentView === 'dev-states' && <DevStatesPage />}
        </div>
      </div>
    </QueryClientProvider>
  );
};

export const App: React.FC = () => {
  return (
    <LanguageProvider>
      <AppContent />
    </LanguageProvider>
  );
};

export default App;
