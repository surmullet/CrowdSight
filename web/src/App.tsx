import React, { useState, useEffect, useCallback } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  Film,
  Plus,
  Layers,
  Cpu,
  FlaskConical,
  Languages,
  RotateCcw,
} from 'lucide-react';
import { SessionLibrary, type SessionSummaryItem } from '@/features/sessions/SessionLibrary';
import { NewSessionWizard, type MediaCatalogItem, type ZoneSetSummary, type ModelProfileInfo } from '@/features/wizard/NewSessionWizard';
import { JobProgressView } from '@/features/jobs/JobProgressView';
import { ReviewWorkspace, type SessionMetadata } from '@/features/review/ReviewWorkspace';
import { ZoneEditor } from '@/features/zones/ZoneEditor';
import { ModelStatusPage } from '@/features/model/ModelStatusPage';
import { DevStatesPage } from '@/features/dev/DevStatesPage';
import { UserNavBadge } from '@/features/auth/UserNavBadge';
import { usePlaybackStore } from '@/shared/state/playbackStore';
import { useAuthStore } from '@/shared/state/authStore';
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

const INITIAL_MEDIA_CATALOG: MediaCatalogItem[] = [
  {
    id: '5cc6461b-1cb0-4700-8305-b01c78780785',
    displayCode: 'MED-0002',
    name: 'crowd6.mp4',
    duration: 25.12,
    fps: 25,
    width: 1280,
    height: 720,
    codec: 'h264',
    browserPlayable: true,
    videoSrc: '/crowd6.mp4',
  },
  {
    id: '4d0e3b31-186f-465f-913a-cab2359bbfa4',
    displayCode: 'MED-0001',
    name: '150.mp4',
    duration: 57.44,
    fps: 25,
    width: 1920,
    height: 1440,
    codec: 'h264',
    browserPlayable: true,
    videoSrc: '/150.mp4',
  },
];

const INITIAL_ZONE_SETS: ZoneSetSummary[] = [];

const DEFAULT_MODEL_PROFILE: ModelProfileInfo = {
  profileId: 'crowd_best_local_v2',
  profileSha256: '83f5287f340ee77b4ba71f3014389146dfd2806283b9cf79427b3ecab6e7a2b2',
  checkpointSha256: '12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc',
  applicabilityStatus: 'EXPERIMENTAL_NO_APPROVAL',
  operationalAlertsAllowed: false,
};

const DEFAULT_SESSION: SessionSummaryItem = {
  id: 'a914bc97-61a1-4840-ab7d-6c20c78afa0f',
  displayCode: 'SES-0001',
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
  const initialSession = urlParams?.get('session') || INITIAL_SESSIONS[0]?.id || 'a914bc97-61a1-4840-ab7d-6c20c78afa0f';

  const [currentView, setCurrentView] = useState<AppView>(initialView);
  const [selectedSessionId, setSelectedSessionId] = useState<string>(initialSession);
  const [dataset150, setDataset150] = useState<any>(null);
  const [datasetSample, setDatasetSample] = useState<any>(null);
  const [datasetCrowd6, setDatasetCrowd6] = useState<any>(null);
  const { locale, toggleLocale, t } = useLanguage();
  const { user } = useAuthStore();
  const isViewer = user?.role === 'VIEWER';
  const [sessions, setSessions] = useState<SessionSummaryItem[]>(INITIAL_SESSIONS);
  const [mediaCatalog, setMediaCatalog] = useState<MediaCatalogItem[]>(INITIAL_MEDIA_CATALOG);
  const [zoneSets, setZoneSets] = useState<ZoneSetSummary[]>(INITIAL_ZONE_SETS);
  const [modelProfile, setModelProfile] = useState<ModelProfileInfo>(DEFAULT_MODEL_PROFILE);
  const [sessionNotes, setSessionNotes] = useState<Record<string, Array<{ id: string; time: number; text: string }>>>({});
  const [activeMediaForZoneEditor, setActiveMediaForZoneEditor] = useState<MediaCatalogItem | null>(null);
  const [sessionDatasetMap, setSessionDatasetMap] = useState<Record<string, any>>({});
  const [reanalyzeTarget, setReanalyzeTarget] = useState<SessionSummaryItem | null>(null);
  const [reanalyzeStride, setReanalyzeStride] = useState<number>(2);
  const [reanalyzeConfidence, setReanalyzeConfidence] = useState<number>(0.18);
  const [reanalyzeModel, setReanalyzeModel] = useState<string>('yolo11n_local');

  const refreshZoneSets = useCallback(async () => {
    try {
      const res = await fetch(`/api/v1/zone-sets?t=${Date.now()}`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          const backendZoneSets: ZoneSetSummary[] = data.map((zs: any) => {
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
          setZoneSets(backendZoneSets);
        }
      }
    } catch (err) {
      console.log('Error fetching zone sets:', err);
    }
  }, []);

  useEffect(() => {
    // 1. Fetch real sessions from SQLite backend
    fetch('/api/v1/sessions')
      .then((res) => (res.ok ? res.json() : []))
      .then((data: any[]) => {
        if (data && data.length > 0) {
          const backendSessions: SessionSummaryItem[] = data.map((item) => ({
            id: item.id,
            displayCode: item.display_code,
            sourceId: item.media_asset_id,
            zoneSetVersionId: item.zone_set_version_id,
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
            if (!prev || !backendSessions.some((b) => b.id === prev)) {
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
            displayCode: m.display_code,
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

    // 3. Fetch real zone sets
    refreshZoneSets();

    // 4. Fetch real model profile
    fetch('/api/v1/model/profile')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) {
          setModelProfile({
            profileId: data.profile_id || 'crowd_best_local_v2',
            profileSha256: data.checkpoint_sha256 ? data.checkpoint_sha256.slice(0, 64) : 'crowd_best_local_v2',
            checkpointSha256: data.checkpoint_sha256 || '',
            applicabilityStatus: data.applicability_status || 'EXPERIMENTAL_NO_APPROVAL',
            operationalAlertsAllowed: Boolean(data.operational_alerts_allowed),
          });
        }
      })
      .catch((err) => console.log('Error fetching model profile:', err));

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

  const fetchSessionDataset = useCallback(async (sessionId: string) => {
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
  }, []);

  const navigateTo = useCallback(
    (view: AppView, sessionId?: string, replace: boolean = false) => {
      const targetSession = sessionId !== undefined ? sessionId : selectedSessionId;
      setCurrentView(view);
      if (sessionId !== undefined) {
        setSelectedSessionId(sessionId);
      }

      if (typeof window !== 'undefined') {
        const params = new URLSearchParams(window.location.search);
        params.set('view', view);
        if (targetSession && (view === 'review' || view === 'progress' || view === 'zones')) {
          params.set('session', targetSession);
        } else {
          params.delete('session');
        }

        const basePath = view === 'dev-states' ? '/dev/states' : '/';
        const newUrl = `${basePath}?${params.toString()}`;
        const stateObj = {
          view,
          sessionId: (view === 'review' || view === 'progress' || view === 'zones') ? targetSession : null,
        };

        if (replace) {
          window.history.replaceState(stateObj, '', newUrl);
        } else {
          const currentState = window.history.state;
          if (currentState?.view !== view || currentState?.sessionId !== stateObj.sessionId) {
            window.history.pushState(stateObj, '', newUrl);
          }
        }
      }
    },
    [selectedSessionId]
  );

  // Initialize history state and popstate listener
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const params = new URLSearchParams(window.location.search);
    const pathView = window.location.pathname === '/dev/states' ? 'dev-states' : null;
    const v = (params.get('view') as AppView) || pathView || 'sessions';
    const s = params.get('session') || initialSession;

    // If initial view is not 'sessions', prime history with 'sessions' first
    // so pressing browser Back returns to 'sessions' instead of exiting the app!
    if (v !== 'sessions') {
      const rootParams = new URLSearchParams();
      rootParams.set('view', 'sessions');
      window.history.replaceState(
        { view: 'sessions', sessionId: null },
        '',
        `/?${rootParams.toString()}`
      );

      const currentParams = new URLSearchParams();
      currentParams.set('view', v);
      if (s && (v === 'review' || v === 'progress' || v === 'zones')) {
        currentParams.set('session', s);
      }
      const currentPath = v === 'dev-states' ? '/dev/states' : '/';
      window.history.pushState(
        { view: v, sessionId: s },
        '',
        `${currentPath}?${currentParams.toString()}`
      );
    } else {
      const rootParams = new URLSearchParams();
      rootParams.set('view', 'sessions');
      window.history.replaceState(
        { view: 'sessions', sessionId: null },
        '',
        `/?${rootParams.toString()}`
      );
    }

    const handlePopState = (event: PopStateEvent) => {
      let targetView: AppView = 'sessions';
      let targetSessionId: string | null = null;

      if (event.state && typeof event.state.view === 'string') {
        targetView = event.state.view as AppView;
        targetSessionId = event.state.sessionId || null;
      } else {
        const curParams = new URLSearchParams(window.location.search);
        const curPathView = window.location.pathname === '/dev/states' ? 'dev-states' : null;
        targetView = (curParams.get('view') as AppView) || curPathView || 'sessions';
        targetSessionId = curParams.get('session');
      }

      setCurrentView(targetView);
      if (targetSessionId) {
        setSelectedSessionId(targetSessionId);
        fetchSessionDataset(targetSessionId);
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => {
      window.removeEventListener('popstate', handlePopState);
    };
  }, [fetchSessionDataset, initialSession]);

  const handleSelectSession = (id: string) => {
    setSelectedSessionId(id);
    const existing = sessionDatasetMap[id];
    if (!existing?.frames?.length) {
      fetchSessionDataset(id);
    }
    navigateTo('review', id);
  };

  const handleDeleteSession = async (id: string) => {
    try {
      const res = await fetch(`/api/v1/sessions/${id}`, { method: 'DELETE' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Không thể xóa phiên phân tích');
      }
      setSessions((prev) => prev.filter((s) => s.id !== id));
      // Đồng bộ lại danh sách phiên từ backend
      const refreshRes = await fetch('/api/v1/sessions');
      if (refreshRes.ok) {
        const data = await refreshRes.json();
        setSessions(data);
      }
    } catch (err: any) {
      console.error('Lỗi khi xóa phiên:', err);
      alert(err.message || 'Lỗi khi xóa phiên phân tích');
      throw err;
    }
  };

  const handleStartSession = async (params: {
    mediaId: string;
    zoneSetId: string;
    zoneSetVersion: number;
    frameStride: number;
    confidence?: number;
    imageSize?: number;
    modelProfile?: string;
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
            confidence: params.confidence !== undefined ? params.confidence : 0.18,
            image_size: params.imageSize || 1280,
            model_profile: params.modelProfile || 'yolo11n_local',
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
        zoneSetVersionId: created.zone_set_version_id,
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
      navigateTo('progress', created.id);
    } catch (err) {
      console.error('Failed to create session:', err);
      throw err;
    }
  };

  const handleOpenReanalyzeModal = (session: SessionSummaryItem) => {
    setReanalyzeTarget(session);
    setReanalyzeStride(2);
    const isTopDown = session.mediaName.includes('150') || session.mediaName.toLowerCase().includes('topdown') || session.mediaName.toLowerCase().includes('drone');
    if (isTopDown) {
      setReanalyzeModel('crowd_best_local_v2');
      setReanalyzeConfidence(0.08);
    } else {
      setReanalyzeModel('yolo11n_local');
      setReanalyzeConfidence(0.18);
    }
  };

  const handleConfirmReanalyze = async () => {
    if (!reanalyzeTarget) return;
    const session = reanalyzeTarget;
    setReanalyzeTarget(null);

    try {
      const mediaId = session.sourceId;
      let zoneSetId = session.zoneSetVersionId;
      if (!zoneSetId) {
        const targetMedia = mediaCatalog.find((m) => m.id === mediaId) || mediaCatalog.find((m) => session.mediaName.includes(m.name));
        const matched = zoneSets.find((z) => {
          const zName = z.name.toLowerCase();
          const mName = (targetMedia?.name || session.mediaName).toLowerCase();
          if (mName.includes('crowd') && zName.includes('crowd')) return true;
          if (mName.includes('150') && zName.includes('150')) return true;
          return false;
        }) || zoneSets[0];
        zoneSetId = matched?.id;
      }

      if (!mediaId || !zoneSetId) {
        alert('Không tìm thấy tệp video hoặc tập vùng tương ứng để phân tích lại.');
        return;
      }

      await handleStartSession({
        mediaId,
        zoneSetId,
        zoneSetVersion: 1,
        frameStride: reanalyzeStride,
        confidence: reanalyzeConfidence,
        modelProfile: reanalyzeModel,
        useSynthetic: false,
      });
    } catch (err: any) {
      console.error('Lỗi khi phân tích lại:', err);
      alert(err.message || 'Lỗi khi khởi động lại phân tích');
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

  const isSynthetic = Boolean(currentSession?.synthetic);

  // Pick dataset based on session: prefer real session dataset from backend if available
  const loadedSessionDataset = sessionDatasetMap[currentSession?.id];
  const isDefaultInitialSample =
    currentSession.id === 'a914bc97-61a1-4840-ab7d-6c20c78afa0f' ||
    currentSession.id === 'session-01-crowd6' ||
    currentSession.id === '8fe5393f-d235-4420-b072-285d479ec03f' ||
    currentSession.id === 'session-03-150' ||
    currentSession.id === 'session-sample-01';
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

  // Synchronize frame observation with video currentTime using binary search on media_time_s
  // This guarantees 100% lock between bounding boxes and video frames regardless of frame_stride or FPS.
  const realFrameObs = React.useMemo(() => {
    if (!activeDataset?.frames || activeDataset.frames.length === 0) return null;
    const frames = activeDataset.frames;

    let low = 0;
    let high = frames.length - 1;
    let bestIdx = 0;
    let minDiff = Infinity;

    while (low <= high) {
      const mid = (low + high) >> 1;
      const f = frames[mid];
      const t = f.media_time_s ?? (f.frame_index !== undefined ? f.frame_index / datasetFps : mid / datasetFps);
      const diff = Math.abs(t - currentTime);

      if (diff < minDiff) {
        minDiff = diff;
        bestIdx = mid;
      }

      if (t < currentTime) {
        low = mid + 1;
      } else {
        high = mid - 1;
      }
    }

    return frames[bestIdx] || null;
  }, [activeDataset, currentTime, datasetFps]);

  const currentFrameIdx = realFrameObs?.frame_index ?? Math.min(
    Math.max(0, Math.round(currentTime * datasetFps)),
    datasetTotalFrames - 1
  );

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
        image_width: activeDataset?.metadata?.width || matchedMedia?.width || (isCrowd6 ? 1280 : 1920),
        image_height: activeDataset?.metadata?.height || matchedMedia?.height || (isCrowd6 ? 720 : is150 ? 1440 : 1080),
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
        image_width: matchedMedia?.width || activeDataset?.metadata?.width || (isCrowd6 ? 1280 : 1920),
        image_height: matchedMedia?.height || activeDataset?.metadata?.height || (isCrowd6 ? 720 : is150 ? 1440 : 1080),
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

  const lastFrameTime = (activeDataset?.frames && activeDataset.frames.length > 0)
    ? (activeDataset.frames[activeDataset.frames.length - 1].media_time_s ?? 0)
    : 0;
  const sessionDuration = Math.max(
    currentSession?.duration || 0,
    lastFrameTime,
    activeDataset?.metadata?.duration || 0,
    (isCrowd6 ? 25.12 : is150 ? 57.44 : 52.47)
  );

  const sampleReviewSession: SessionMetadata = {
    sessionId: currentSession.id,
    sourceId: currentSession.sourceId,
    mediaName: currentSession.mediaName,
    duration: sessionDuration,
    imageWidth: activeDataset?.metadata?.width || matchedMedia?.width || (isCrowd6 ? 1280 : 1920),
    imageHeight: activeDataset?.metadata?.height || matchedMedia?.height || (isCrowd6 ? 720 : (is150 ? 1440 : 1080)),
    synthetic: Boolean(currentSession.synthetic),
    modelProfileId: activeDataset?.metadata?.model || 'models/best.pt',
    modelProfileSha256: 'crowd_best_local_v2',
    checkpointSha256: 'best.pt',
    videoSrc: videoSrc,
    heatmapUrl: `/api/v1/sessions/${currentSession.id}/heatmap`,
  };

  const qualityIntervals = React.useMemo(() => {
    if (!activeDataset?.frames || activeDataset.frames.length === 0) {
      return [{ startTime: 0, endTime: sessionDuration, quality: 'VALID' as const }];
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
      currentInterval.endTime = Math.max(currentInterval.endTime, sessionDuration);
      intervals.push(currentInterval);
    }
    return intervals.length > 0
      ? intervals
      : [{ startTime: 0, endTime: sessionDuration, quality: 'VALID' as const }];
  }, [activeDataset, sessionDuration]);

  const zoneTrends = React.useMemo(() => {
    if (!sampleZones || sampleZones.length === 0) return [];

    if (activeDataset?.frames && activeDataset.frames.length > 0) {
      const frames = activeDataset.frames;
      const duration = sessionDuration;
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

  // Real Operator Notes: fetch from SQLite backend for current session
  useEffect(() => {
    if (!currentSession?.id) return;
    fetch(`/api/v1/sessions/${currentSession.id}/notes`)
      .then((res) => (res.ok ? res.json() : []))
      .then((data: any[]) => {
        if (Array.isArray(data)) {
          setSessionNotes((prev) => ({
            ...prev,
            [currentSession.id]: data.map((n) => ({
              id: n.id,
              time: n.media_time_s,
              text: n.text,
            })),
          }));
        }
      })
      .catch((err) => console.log('Error fetching session notes:', err));
  }, [currentSession?.id]);

  const handleAddSessionNote = async (text: string, mediaTime: number) => {
    if (!currentSession?.id) return;
    try {
      const res = await fetch(`/api/v1/sessions/${currentSession.id}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ media_time_s: mediaTime, text, author: 'operator' }),
      });
      if (res.ok) {
        const created = await res.json();
        setSessionNotes((prev) => ({
          ...prev,
          [currentSession.id]: [
            ...(prev[currentSession.id] || []),
            { id: created.id, time: created.media_time_s, text: created.text },
          ],
        }));
      }
    } catch (err) {
      console.error('Lỗi khi thêm ghi chú:', err);
    }
  };

  const handleDeleteSessionNote = async (noteId: string) => {
    if (!currentSession?.id) return;
    try {
      const res = await fetch(`/api/v1/sessions/${currentSession.id}/notes/${noteId}`, {
        method: 'DELETE',
      });
      if (res.ok || res.status === 204) {
        setSessionNotes((prev) => ({
          ...prev,
          [currentSession.id]: (prev[currentSession.id] || []).filter((n) => n.id !== noteId),
        }));
      }
    } catch (err) {
      console.error('Lỗi khi xóa ghi chú:', err);
    }
  };


  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-brand-abyssal text-brand-text-primary flex flex-col font-sans">
        {/* Navigation Bar */}
        <nav className="h-12 bg-brand-deck border-b border-brand-border px-6 flex items-center justify-between z-40 select-none">
          <div className="flex items-center gap-6">
            {/* Logo */}
            <button
              type="button"
              onClick={() => navigateTo('sessions')}
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
                onClick={() => navigateTo('sessions')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded transition-colors ${
                  currentView === 'sessions'
                    ? 'bg-brand-surface text-brand-gold font-medium'
                    : 'text-brand-text-muted hover:text-brand-text-primary'
                }`}
              >
                <Film className="w-3.5 h-3.5" />
                <span>{t.nav.sessions}</span>
              </button>

              {!isViewer && (
                <button
                  type="button"
                  onClick={() => navigateTo('wizard')}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded transition-colors ${
                    currentView === 'wizard'
                      ? 'bg-brand-surface text-brand-gold font-medium'
                      : 'text-brand-text-muted hover:text-brand-text-primary'
                  }`}
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>{t.nav.wizard}</span>
                </button>
              )}

              <button
                type="button"
                onClick={() => navigateTo('zones')}
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
                onClick={() => navigateTo('model')}
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
                onClick={() => navigateTo('dev-states')}
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
            <UserNavBadge />
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
              onNewSession={() => navigateTo('wizard')}
              onDeleteSession={handleDeleteSession}
              onReanalyzeSession={handleOpenReanalyzeModal}
            />
          )}

          {currentView === 'wizard' && (
            <NewSessionWizard
              mediaCatalog={mediaCatalog}
              zoneSets={zoneSets}
              modelProfile={modelProfile}
              onCreateZoneSet={(mediaId) => {
                const found = mediaCatalog.find((m) => m.id === mediaId) || mediaCatalog[0];
                setActiveMediaForZoneEditor(found || null);
                navigateTo('zones');
              }}
              onUploadMedia={handleUploadMedia}
              onSubmit={handleStartSession}
              onCancel={() => navigateTo('sessions')}
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
                navigateTo('review', selectedSessionId);
              }}
              onOpenPartialResults={async () => {
                setSessions((prev) =>
                  prev.map((s) => (s.id === selectedSessionId ? { ...s, status: 'COMPLETED', progress: 1.0 } : s))
                );
                await fetchSessionDataset(selectedSessionId);
                navigateTo('review', selectedSessionId);
              }}
              onRetry={() => currentSession && handleOpenReanalyzeModal(currentSession)}
              onBackToLibrary={() => navigateTo('sessions')}
            />
          )}

          {currentView === 'review' && (
            <ReviewWorkspace
              session={sampleReviewSession}
              zones={sampleZones}
              onBack={() => navigateTo('sessions')}
              activeObservation={activeObservation}
              activeReadings={activeReadings}
              qualityIntervals={qualityIntervals}
              zoneTrends={zoneTrends}
              peaks={peaks}
              initialNotes={sessionNotes[currentSession?.id] || []}
              onAddNote={handleAddSessionNote}
              onDeleteNote={handleDeleteSessionNote}
              onExportCsv={handleExportCsv}
              onExportJsonl={handleExportJsonl}
              onReanalyze={() => currentSession && handleOpenReanalyzeModal(currentSession)}
              onEditZones={() => {
                const found = mediaCatalog.find((m) => m.id === currentSession.sourceId || currentSession.mediaName.includes(m.name)) || mediaCatalog[0];
                setActiveMediaForZoneEditor(found || null);
                navigateTo('zones');
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

            // Compute appropriate initial zones matching the specific video aspect ratio
            const initialZonesForMedia = isTarget150
              ? [
                  { zoneId: 'zone-a', name: 'Khu vực Giám sát A (Bên trái)', color: '#0072B2', vertices: [[192, 432], [1056, 432], [960, 1368], [96, 1368]] as [number, number][] },
                  { zoneId: 'zone-b', name: 'Khu vực Giám sát B (Bên phải)', color: '#009E73', vertices: [[1056, 360], [1824, 360], [1824, 1368], [960, 1368]] as [number, number][] },
                ]
              : (targetName.includes('crowd') && !targetName.includes('crowd6'))
                ? [
                    { zoneId: 'zone-a', name: 'Khu vực A (Bên trái)', color: '#0072B2', vertices: [[100, 150], [920, 150], [860, 1020], [100, 1020]] as [number, number][] },
                    { zoneId: 'zone-b', name: 'Khu vực B (Bên phải)', color: '#009E73', vertices: [[960, 150], [1820, 150], [1820, 1020], [920, 1020]] as [number, number][] },
                  ]
                : targetName.includes('crowd6')
                  ? [
                      { zoneId: 'zone-a', name: 'Khu vực A', color: '#0072B2', vertices: [[0, 8], [659, 0], [609, 720], [0, 714]] as [number, number][] },
                      { zoneId: 'zone-b', name: 'Khu vực B', color: '#009E73', vertices: [[661, 0], [1280, 0], [1280, 716], [610, 720]] as [number, number][] },
                    ]
                  : [
                      { zoneId: 'zone-a', name: 'Khu vực A', color: '#0072B2', vertices: [[Math.round(width * 0.05), Math.round(height * 0.1)], [Math.round(width * 0.48), Math.round(height * 0.1)], [Math.round(width * 0.45), Math.round(height * 0.9)], [Math.round(width * 0.05), Math.round(height * 0.9)]] as [number, number][] },
                      { zoneId: 'zone-b', name: 'Khu vực B', color: '#009E73', vertices: [[Math.round(width * 0.52), Math.round(height * 0.1)], [Math.round(width * 0.95), Math.round(height * 0.1)], [Math.round(width * 0.95), Math.round(height * 0.9)], [Math.round(width * 0.52), Math.round(height * 0.9)]] as [number, number][] },
                    ];

            return (
              <ZoneEditor
                key={`zone-editor-${targetMedia?.id || currentSession.id}`}
                initialZoneSetName={targetMedia?.name ? `Khu vực giám sát (${targetMedia.name.split(' ')[0]})` : (currentSession.zoneSetName || 'Khu vực quan sát')}
                initialZones={initialZonesForMedia}
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

                  // Persist new zone set version to backend database
                  try {
                    const zoneSetId = isTarget150
                      ? 'zones-150'
                      : (targetName.includes('crowd') && !targetName.includes('crowd6'))
                        ? 'zones-media-03-crowd'
                        : targetName.includes('crowd6')
                          ? 'zones-crowd6'
                          : `zones-${targetMedia?.id || 'custom'}`;

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
                          name: data.name || (isTarget150 ? 'Khu vực giám sát (150.mp4)' : `Khu vực giám sát (${targetMedia?.name || 'video'})`),
                          ...payload,
                        }),
                      });
                    }
                    await refreshZoneSets();
                  } catch (err) {
                    console.warn('Could not persist zone set to backend database:', err);
                  }

                  if (activeMediaForZoneEditor) {
                    navigateTo('wizard');
                  } else {
                    navigateTo('review');
                  }
                }}
                onCancel={() => {
                  if (activeMediaForZoneEditor) {
                    navigateTo('wizard');
                  } else {
                    navigateTo('review');
                  }
                }}
              />
            );
          })()}

          {currentView === 'model' && (
            <ModelStatusPage
              onBack={() => navigateTo('sessions')}
              modelProfileId={modelProfile.profileId}
              modelProfileSha256={modelProfile.profileSha256}
              checkpointSha256={modelProfile.checkpointSha256}
              applicabilityStatus={modelProfile.applicabilityStatus}
              operationalAlertsAllowed={modelProfile.operationalAlertsAllowed}
            />
          )}

          {currentView === 'dev-states' && <DevStatesPage onBack={() => navigateTo('sessions')} />}
        </div>

        {/* Re-analyze Configuration Modal */}
        {reanalyzeTarget && (
          <div
            role="dialog"
            aria-modal="true"
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm"
          >
            <div className="bg-brand-surface border border-brand-border rounded-2xl max-w-md w-full p-6 shadow-2xl text-xs space-y-5">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-brand-gold/10 border border-brand-gold/30 rounded-xl text-brand-gold">
                  <RotateCcw className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-brand-text-primary">
                    Cấu hình phân tích lại video
                  </h3>
                  <p className="text-[11px] text-brand-text-muted">
                    {reanalyzeTarget.mediaName}
                  </p>
                </div>
              </div>

              {/* Frame stride option */}
              <div className="space-y-3 p-4 bg-brand-abyssal/60 border border-brand-border rounded-xl">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-brand-text-primary">
                    Bước nhảy khung hình (frame_stride):
                  </span>
                  <span className="font-mono text-sm font-bold text-brand-gold">
                    {reanalyzeStride}
                  </span>
                </div>

                <input
                  type="range"
                  min="1"
                  max="15"
                  value={reanalyzeStride}
                  onChange={(e) => setReanalyzeStride(parseInt(e.target.value, 10))}
                  className="w-full accent-brand-gold bg-brand-border rounded cursor-pointer"
                />

                {/* Quick Presets */}
                <div className="grid grid-cols-4 gap-1.5 pt-1">
                  {[
                    { label: '1x (Chi tiết)', stride: 1 },
                    { label: '2x (Khuyên dùng)', stride: 2 },
                    { label: '5x (Nhanh)', stride: 5 },
                    { label: '10x (Siêu tốc)', stride: 10 },
                  ].map((preset) => (
                    <button
                      key={preset.stride}
                      type="button"
                      onClick={() => setReanalyzeStride(preset.stride)}
                      className={`py-1 px-1.5 rounded text-[10px] font-medium border transition-colors ${
                        reanalyzeStride === preset.stride
                          ? 'bg-brand-gold/20 border-brand-gold text-brand-gold font-bold'
                          : 'bg-brand-surface border-brand-border text-brand-text-muted hover:text-brand-text-primary'
                      }`}
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>

                {/* Explanation & Impact preview */}
                <div className="p-3 bg-brand-surface border border-brand-border/70 rounded-lg space-y-1.5 text-[11px] text-brand-text-muted">
                  <div className="flex justify-between text-brand-text-primary">
                    <span>Số khung hình xử lý:</span>
                    <span className="font-mono font-semibold text-brand-gold">
                      ~{Math.round(((reanalyzeTarget.duration || 57) * 25) / reanalyzeStride)} khung hình
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Tốc độ xử lý dự kiến:</span>
                    <span className="font-mono text-emerald-400">
                      Nhanh gấp ~{reanalyzeStride}x lần
                    </span>
                  </div>
                  <p className="text-[10px] pt-1 text-brand-text-muted/80 leading-normal border-t border-brand-border/40">
                    {reanalyzeStride === 1
                      ? '⚡ Quét toàn bộ mọi khung hình (100%), độ chính xác tuyệt đối, thời gian xử lý tiêu chuẩn.'
                      : `⚡ Bỏ qua ${reanalyzeStride - 1} khung và quét 1 khung, giúp tăng tốc độ xử lý gấp ~${reanalyzeStride} lần mà vẫn bắt kịp xu hướng mật độ.`}
                  </p>
                </div>
              </div>

              {/* Confidence option */}
              <div className="space-y-3 p-4 bg-brand-abyssal/60 border border-brand-border rounded-xl">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-brand-text-primary block">
                      Độ nhạy phát hiện (Confidence):
                    </span>
                    <span className="text-[10px] text-brand-text-muted">
                      Hạ thấp để phát hiện cả người che ô, áo mưa, người già chống gậy
                    </span>
                  </div>
                  <span className="font-mono text-sm font-bold text-amber-400">
                    {reanalyzeConfidence.toFixed(2)}
                  </span>
                </div>

                <input
                  type="range"
                  min="0.05"
                  max="0.50"
                  step="0.01"
                  value={reanalyzeConfidence}
                  onChange={(e) => setReanalyzeConfidence(parseFloat(e.target.value))}
                  className="w-full accent-amber-400 bg-brand-border rounded cursor-pointer"
                />

                {/* Quick Presets */}
                <div className="grid grid-cols-4 gap-1.5 pt-1">
                  {(reanalyzeTarget?.mediaName.includes('150') || reanalyzeModel === 'crowd_best_local_v2'
                    ? [
                        { label: '0.08 (Góc trần/Đề xuất)', conf: 0.08 },
                        { label: '0.10 (Nhạy cao)', conf: 0.10 },
                        { label: '0.15 (Vừa phải)', conf: 0.15 },
                        { label: '0.25 (Tiêu chuẩn)', conf: 0.25 },
                      ]
                    : [
                        { label: '0.15 (Nhạy tối đa)', conf: 0.15 },
                        { label: '0.18 (Đề xuất)', conf: 0.18 },
                        { label: '0.25 (Tiêu chuẩn)', conf: 0.25 },
                        { label: '0.35 (Nghiêm ngặt)', conf: 0.35 },
                      ]
                  ).map((preset) => (
                    <button
                      key={preset.conf}
                      type="button"
                      onClick={() => setReanalyzeConfidence(preset.conf)}
                      className={`py-1 px-1.5 rounded text-[10px] font-medium border transition-colors ${
                        Math.abs(reanalyzeConfidence - preset.conf) < 0.005
                          ? 'bg-amber-400/20 border-amber-400 text-amber-300 font-bold'
                          : 'bg-brand-surface border-brand-border text-brand-text-muted hover:text-brand-text-primary'
                      }`}
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>

                <p className="text-[10px] text-brand-text-muted/80 leading-normal border-t border-brand-border/40 pt-1.5">
                  {reanalyzeModel === 'crowd_best_local_v2'
                    ? '🎯 Góc trên đỉnh đầu (Top-Down): Khuyên dùng mức 0.08 – 0.10 để bắt trọn từng đầu người/nón cam trong đám đông đông đúc.'
                    : reanalyzeConfidence <= 0.18
                    ? '🎯 Góc nghiêng/đường phố: Khuyên dùng 0.18 để quét trọn vẹn cả người cận cảnh, che ô, cúi lưng, áo mưa.'
                    : '🛡️ Độ nhạy nghiêm ngặt: Chỉ nhận diện khi AI có độ tự tin cao.'}
                </p>
              </div>

              {/* Model Selection option */}
              <div className="space-y-2 p-3 bg-brand-abyssal/60 border border-brand-border rounded-xl text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-brand-text-primary">
                    Mô hình AI nhận diện:
                  </span>
                  <span className="text-[10px] text-emerald-400 font-mono">
                    {reanalyzeModel === 'yolo11n_local' ? 'COCO Đa Góc Nhìn' : 'VisDrone Góc Cao'}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setReanalyzeModel('yolo11n_local');
                      if (reanalyzeConfidence < 0.15) setReanalyzeConfidence(0.18);
                    }}
                    className={`p-2.5 rounded-lg border text-left transition-all ${
                      reanalyzeModel === 'yolo11n_local'
                        ? 'bg-emerald-950/40 border-emerald-500/80 text-emerald-200'
                        : 'bg-brand-surface border-brand-border text-brand-text-muted hover:text-brand-text-primary'
                    }`}
                  >
                    <div className="font-bold text-[11px] flex items-center justify-between">
                      <span>YOLO11 Toàn Năng</span>
                      {(!reanalyzeTarget?.mediaName.includes('150')) && (
                        <span className="text-[9px] bg-emerald-500/20 text-emerald-400 px-1 rounded font-semibold">Khuyên dùng</span>
                      )}
                    </div>
                    <p className="text-[10px] text-brand-text-muted mt-1 leading-tight">
                      Góc nhìn camera đường phố / CCTV nghiêng (thấy thân người, chân tay, cận cảnh).
                    </p>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setReanalyzeModel('crowd_best_local_v2');
                      if (reanalyzeConfidence > 0.15) setReanalyzeConfidence(0.08);
                    }}
                    className={`p-2.5 rounded-lg border text-left transition-all ${
                      reanalyzeModel === 'crowd_best_local_v2'
                        ? 'bg-amber-950/40 border-amber-500/80 text-amber-200'
                        : 'bg-brand-surface border-brand-border text-brand-text-muted hover:text-brand-text-primary'
                    }`}
                  >
                    <div className="font-bold text-[11px] flex items-center justify-between">
                      <span>YOLO11 Finetuned</span>
                      {reanalyzeTarget?.mediaName.includes('150') && (
                        <span className="text-[9px] bg-amber-500/20 text-amber-300 px-1 rounded font-semibold">Khuyên dùng video này</span>
                      )}
                    </div>
                    <p className="text-[10px] text-brand-text-muted mt-1 leading-tight">
                      Chuyên camera góc cao nhìn thẳng từ trần xuống đỉnh đầu (Flycam/Drone/Cửa kiểm soát).
                    </p>
                  </button>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-3 pt-1">
                <button
                  type="button"
                  onClick={() => setReanalyzeTarget(null)}
                  className="px-4 py-2 bg-brand-abyssal hover:bg-brand-border border border-brand-border text-brand-text-primary rounded-lg transition-colors"
                >
                  Hủy
                </button>
                <button
                  type="button"
                  onClick={handleConfirmReanalyze}
                  className="px-5 py-2 bg-brand-gold hover:bg-brand-gold/90 text-brand-abyssal font-bold rounded-lg transition-colors flex items-center gap-1.5 shadow"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Bắt đầu phân tích lại</span>
                </button>
              </div>
            </div>
          </div>
        )}
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
