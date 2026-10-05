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

function normalizeDataset(data: any): any {
  if (!data) return null;
  let frames = data.frames;
  if (frames && !Array.isArray(frames)) {
    frames = Object.values(frames);
  }
  return {
    ...data,
    frames: frames || [],
  };
}

const MOCK_MEDIA_CATALOG: MediaCatalogItem[] = [
  {
    id: 'media-01-crowd6',
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
    id: 'media-02-150',
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
    id: 'zsv-crowd6-v2',
    name: 'Khu vực giám sát (crowd6.mp4)',
    version: 2,
    zoneCount: 2,
  },
  {
    id: 'zsv-150-v3',
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
  id: 'session-01-crowd6',
  sourceId: 'crowd6.mp4',
  mediaName: 'crowd6.mp4 (AI Quét Thật)',
  duration: 25.12,
  status: 'COMPLETED',
  progress: 1.0,
  synthetic: false,
  createdAt: '2026-10-02 14:00:00',
  zoneSetName: 'Khu vực giám sát (crowd6.mp4)',
  videoSrc: '/crowd6.mp4',
  qualityBreakdown: {
    validPct: 100,
    partialPct: 0,
    unknownPct: 0,
    stalePct: 0,
  },
};

const INITIAL_SESSIONS: SessionSummaryItem[] = [DEFAULT_SESSION];

const AppContent: React.FC = () => {
  const urlParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
  const initialView = (urlParams?.get('view') as AppView) || 'sessions';
  const initialSession = urlParams?.get('session') || INITIAL_SESSIONS[0]?.id || 'session-01-crowd6';

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
          setSessions(backendSessions);
          setSelectedSessionId((prev) => {
            if (!prev || prev.startsWith('session-') || !backendSessions.some((b) => b.id === prev)) {
              return backendSessions[0]?.id || prev;
            }
            return prev;
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
            videoSrc: `/api/v1/media/${m.id}/stream?v=${m.sha256 ? m.sha256.slice(0, 10) : '0'}`,
          }));
          setMediaCatalog((prev) => {
            // Only keep newly uploaded local blobs (with media-upload- prefix)
            const uploadedUserBlobs = prev.filter((p) => p.id.startsWith('media-upload-'));
            return [...backendMedia, ...uploadedUserBlobs];
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
        if (data) setDataset150(normalizeDataset(data));
      })
      .catch((err) => console.log('150 observations error:', err));

    fetch('/sample_real_observations.json')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setDatasetSample(normalizeDataset(data));
      })
      .catch((err) => console.log('sample observations error:', err));

    fetch('/media_crowd6_observations.json')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setDatasetCrowd6(normalizeDataset(data));
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
        // Replace previous duplicate entry if same ID or name was re-uploaded
        setMediaCatalog((prev) => [
          mediaItem,
          ...prev.filter((m) => m.id !== data.id && m.name !== data.display_name),
        ]);
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
    setMediaCatalog((prev) => [
      fallbackItem,
      ...prev.filter((m) => m.name !== file.name),
    ]);
    return fallbackItem;
  };

  useEffect(() => {
    if (window.location.pathname === '/dev/states') {
      setCurrentView('dev-states');
    }
  }, []);

  const fetchSessionDataset = async (sessionId: string) => {
    if (!sessionId) return null;
    try {
      const res = await fetch(`/api/v1/sessions/${sessionId}/dataset?t=${Date.now()}`);
      if (res.ok) {
        const raw = await res.json();
        const data = normalizeDataset(raw);
        if (data && data.frames && data.frames.length > 0) {
          setSessionDatasetMap((prev) => ({ ...prev, [sessionId]: data }));
          return data;
        }
      }
    } catch (err) {
      console.log('Dataset fetch error:', err);
    }
    return null;
  };

  const handleSelectSession = (id: string) => {
    setSelectedSessionId(id);
    const existing = sessionDatasetMap[id];
    if (!existing?.frames?.length) {
      fetchSessionDataset(id);
    }
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

  // Load dataset for selected session if not already in memory with real frames
  useEffect(() => {
    if (!selectedSessionId) return;
    const existing = sessionDatasetMap[selectedSessionId];
    if (existing?.frames?.length > 0) return;

    fetchSessionDataset(selectedSessionId);
  }, [selectedSessionId, sessionDatasetMap]);

  // Ensure dataset is loaded whenever switching to review view
  useEffect(() => {
    if (currentView === 'review' && selectedSessionId) {
      const existing = sessionDatasetMap[selectedSessionId];
      if (!existing?.frames?.length) {
        fetchSessionDataset(selectedSessionId);
      }
    }
  }, [currentView, selectedSessionId, sessionDatasetMap]);

  const { currentTime } = usePlaybackStore();

  const currentSession: SessionSummaryItem =
    sessions.find((s) => s.id === selectedSessionId) ?? sessions[0] ?? DEFAULT_SESSION;

  const sessionNameLower = (currentSession?.mediaName || '').toLowerCase();
  const sessionSourceLower = (currentSession?.sourceId || '').toLowerCase();

  const isCrowd6 = sessionNameLower.includes('crowd6') || sessionSourceLower.includes('crowd6');
  const is150 = !isCrowd6 && (sessionNameLower.includes('150') || sessionSourceLower.includes('150'));
  const isSample = !isCrowd6 && !is150 && (sessionNameLower.includes('sample') || sessionSourceLower.includes('sample'));

  const isSynthetic = Boolean(currentSession?.synthetic) || (!useRealAI && !is150 && !isSample && !isCrowd6);

  // Pick dataset based on session: prefer real session dataset from backend if available
  const loadedSessionDataset = sessionDatasetMap[currentSession?.id];
  const isDefaultInitialSample = currentSession.id === 'session-01-crowd6' || currentSession.id === 'session-03-150' || currentSession.id === 'session-sample-01';
  const activeDataset = (loadedSessionDataset && loadedSessionDataset.frames && loadedSessionDataset.frames.length > 0)
    ? loadedSessionDataset
    : (isDefaultInitialSample
      ? (isCrowd6 ? datasetCrowd6 : is150 ? dataset150 : datasetSample)
      : (loadedSessionDataset || null));

  const sampleZones = (activeDataset?.zones && activeDataset.zones.length > 0)
    ? activeDataset.zones
    : (isDefaultInitialSample && is150
      ? [
          {
            zone_id: 'zone-a',
            name: 'Khu vực Giám sát A (Bên trái)',
            color: '#0072B2',
            vertices: [[192, 432], [1056, 432], [960, 1368], [96, 1368]] as [number, number][],
          },
          {
            zone_id: 'zone-b',
            name: 'Khu vực Giám sát B (Bên phải)',
            color: '#009E73',
            vertices: [[1056, 360], [1824, 360], [1824, 1368], [960, 1368]] as [number, number][],
          },
        ]
      : (isDefaultInitialSample && isCrowd6
        ? [
            {
              zone_id: 'zone-a',
              name: 'Khu vực A (crowd6)',
              color: '#0072B2',
              vertices: [[0, 8], [659, 0], [609, 720], [0, 714]] as [number, number][],
            },
            {
              zone_id: 'zone-b',
              name: 'Khu vực B (crowd6)',
              color: '#009E73',
              vertices: [[661, 0], [1280, 0], [1280, 716], [610, 720]] as [number, number][],
            },
          ]
        : []
      ));

  const datasetFps = activeDataset?.metadata?.fps || 25;
  const datasetTotalFrames = activeDataset?.metadata?.totalFrames || activeDataset?.frames?.length || (isCrowd6 ? 628 : is150 ? 1436 : 1242);

  const currentFrameIdx = Math.min(
    Math.max(0, Math.round(currentTime * datasetFps)),
    datasetTotalFrames - 1
  );

  const realFrameObs = activeDataset?.frames ? activeDataset.frames[currentFrameIdx] : null;

  const activeQuality: FrameQuality = (!isSynthetic && realFrameObs)
    ? (realFrameObs.quality || 'VALID')
    : 'VALID';

  // Determine videoSrc accurately: prioritize active session stream (with cache busting token) or local uploaded blob
  const matchedMedia = mediaCatalog.find(
    (m) => m.id === currentSession.sourceId || currentSession.mediaName === m.name
  );

  let videoSrc = currentSession.videoSrc || matchedMedia?.videoSrc;
  if (!videoSrc) {
    if (currentSession.sourceId && !currentSession.sourceId.startsWith('session-')) {
      videoSrc = `/api/v1/media/${currentSession.sourceId}/stream`;
    } else if (isCrowd6) {
      videoSrc = '/crowd6.mp4';
    } else if (is150) {
      videoSrc = '/150.mp4';
    } else if (isSample) {
      videoSrc = '/sample.mp4';
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
        fully_observed_zones: sampleZones.map((z: any) => z.zone_id),
        confidence_semantics: 'RAW_MODEL_SCORE',
        quality: activeQuality,
        detections: realFrameObs.detections || [],
      }
    : {
        source_id: currentSession?.sourceId || (isCrowd6 ? 'crowd6.mp4' : is150 ? '150.mp4' : 'video.mp4'),
        session_id: currentSession?.id || selectedSessionId,
        model_profile_id: activeDataset?.metadata?.model || 'models/best.pt',
        model_profile_sha256: 'crowd_best_local_v2',
        checkpoint_sha256: 'best.pt',
        frame_index: currentFrameIdx,
        media_time_s: +(currentFrameIdx / datasetFps).toFixed(2),
        image_width: matchedMedia?.width || (isCrowd6 ? 1280 : 1920),
        image_height: matchedMedia?.height || (isCrowd6 ? 720 : is150 ? 1440 : 1080),
        observation_valid: true,
        registration_valid: false,
        fully_observed_zones: sampleZones.map((z: any) => z.zone_id),
        confidence_semantics: 'RAW_MODEL_SCORE',
        quality: activeQuality,
        detections: [],
      };

  const activeReadings: ZoneReading[] = (realFrameObs?.zone_readings && realFrameObs.zone_readings.length > 0)
    ? realFrameObs.zone_readings.map((zr: any) => ({
        status: (zr.status === 'NOT_FULLY_OBSERVED' || zr.status === 'UNKNOWN' ? zr.status : 'COUNTED') as ZoneReading['status'],
        count: zr.count ?? 0,
        zoneId: zr.zoneId || zr.zone_id,
        zoneName: zr.zoneName || zr.name,
      }))
    : (sampleZones && sampleZones.length > 0)
      ? sampleZones.map((z: any) => {
          const count = (realFrameObs?.detections || []).filter((d: any) => {
            const px = d.bbox_xyxy ? (d.bbox_xyxy[0] + d.bbox_xyxy[2]) / 2 : d.x * (activeDataset?.metadata?.width || (isCrowd6 ? 1280 : 1920));
            const py = d.bbox_xyxy ? d.bbox_xyxy[3] : d.y * (activeDataset?.metadata?.height || (isCrowd6 ? 720 : 1440));
            return isPointInPolygon([px, py], z.vertices);
          }).length;
          return {
            status: 'COUNTED' as const,
            count,
            zoneId: z.zone_id,
            zoneName: z.name,
          };
        })
      : [];

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

  const qualityIntervals = React.useMemo(() => {
    if (!activeDataset?.frames || activeDataset.frames.length === 0) {
      return [{ startTime: 0, endTime: sampleReviewSession.duration, quality: 'VALID' as const }];
    }
    const intervals: { startTime: number; endTime: number; quality: FrameQuality }[] = [];
    let currentInterval: { startTime: number; endTime: number; quality: FrameQuality } | null = null;

    for (const f of activeDataset.frames) {
      const q: FrameQuality = f.quality || 'VALID';
      const t: number = f.media_time_s ?? 0;
      if (!currentInterval) {
        currentInterval = { startTime: t, endTime: t, quality: q };
      } else if (currentInterval.quality === q) {
        currentInterval.endTime = t;
      } else {
        intervals.push(currentInterval);
        currentInterval = { startTime: t, endTime: t, quality: q };
      }
    }
    if (currentInterval) {
      intervals.push(currentInterval);
    }
    return intervals.length > 0
      ? intervals
      : [{ startTime: 0, endTime: sampleReviewSession.duration, quality: 'VALID' as const }];
  }, [activeDataset, sampleReviewSession.duration]);

  const zoneTrends = React.useMemo(() => {
    if (!sampleZones || sampleZones.length === 0) return [];

    if (activeDataset?.frames && activeDataset.frames.length > 0) {
      const frames = activeDataset.frames;
      const duration = activeDataset.metadata?.duration || currentSession.duration || 30;
      const step = Math.max(1, Math.round(duration / 25));
      const sampleTimes: number[] = [];
      for (let t = 0; t <= duration; t += step) {
        sampleTimes.push(t);
      }
      const lastSample = sampleTimes[sampleTimes.length - 1];
      if (lastSample !== undefined && lastSample < duration) {
        sampleTimes.push(duration);
      }

      return sampleZones.map((z: any) => {
        const points = sampleTimes.map((time) => {
          const frameIdx = Math.min(
            Math.max(0, Math.round(time * datasetFps)),
            frames.length - 1
          );
          const f = frames[frameIdx];
          let count = 0;
          if (f?.zone_readings && f.zone_readings.length > 0) {
            const zr = f.zone_readings.find((r: any) => (r.zoneId || r.zone_id) === z.zone_id);
            if (zr) count = zr.count ?? 0;
          } else if (f?.detections) {
            count = f.detections.filter((d: any) => {
              const px = d.bbox_xyxy ? (d.bbox_xyxy[0] + d.bbox_xyxy[2]) / 2 : d.x * (activeDataset.metadata?.width || 1920);
              const py = d.bbox_xyxy ? d.bbox_xyxy[3] : d.y * (activeDataset.metadata?.height || 1080);
              return isPointInPolygon([px, py], z.vertices);
            }).length;
          }
          return { time, count };
        });

        return {
          zoneId: z.zone_id,
          name: z.name,
          color: z.color || '#0072B2',
          points,
        };
      });
    }

    return sampleZones.map((z: any) => ({
      zoneId: z.zone_id,
      name: z.name,
      color: z.color || '#0072B2',
      points: [
        { time: 0, count: 0 },
        { time: currentSession.duration || 30, count: 0 },
      ],
    }));
  }, [activeDataset, sampleZones, currentSession.duration, datasetFps]);

  const peaks = React.useMemo(() => {
    const peakList: any[] = [];
    zoneTrends.forEach((zt: any) => {
      let maxPt = { time: 0, count: 0 };
      zt.points.forEach((pt: any) => {
        if (pt.count !== null && pt.count > maxPt.count) {
          maxPt = { time: pt.time, count: pt.count };
        }
      });
      if (maxPt.count > 0) {
        peakList.push({
          time: maxPt.time,
          count: maxPt.count,
          zoneId: zt.zoneId,
          label: `Đỉnh ${zt.name}: ${maxPt.count} người`,
        });
      }
    });
    return peakList;
  }, [zoneTrends]);

  const initialNotes = React.useMemo(() => {
    return [
      { id: 'n1', time: 5, text: `Đã phân tích mô hình YOLO trên ${currentSession.mediaName}.` },
    ];
  }, [currentSession.mediaName]);


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
              onComplete={async () => {
                setSessions((prev) =>
                  prev.map((s) => (s.id === selectedSessionId ? { ...s, status: 'COMPLETED', progress: 1.0 } : s))
                );
                await fetchSessionDataset(selectedSessionId);
                setCurrentView('review');
              }}
              onOpenPartialResults={async () => {
                setSessions((prev) =>
                  prev.map((s) => (s.id === selectedSessionId ? { ...s, status: 'COMPLETED', progress: 1.0 } : s))
                );
                await fetchSessionDataset(selectedSessionId);
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
              qualityIntervals={qualityIntervals}
              zoneTrends={zoneTrends}
              peaks={peaks}
              initialNotes={initialNotes}
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
