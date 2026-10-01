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

const MOCK_MEDIA_CATALOG: MediaCatalogItem[] = [
  {
    id: 'media-150',
    name: '150.mp4 (Video Vừa Tải Lên)',
    duration: 57.44,
    fps: 25,
    width: 1920,
    height: 1440,
    codec: 'h264',
    browserPlayable: true,
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

const MOCK_ZONE_SETS: ZoneSetSummary[] = [
  {
    id: 'zs-default',
    name: 'Khu vực Giám sát A & B (150.mp4)',
    version: 1,
    zoneCount: 2,
  },
  {
    id: 'zs-gates',
    name: 'Cổng đón trả khách',
    version: 2,
    zoneCount: 2,
  },
];

const MOCK_MODEL_PROFILE: ModelProfileInfo = {
  profileId: 'yolo11n_person_detector',
  profileSha256: '0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1',
  checkpointSha256: '0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1',
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
  const [currentView, setCurrentView] = useState<AppView>('sessions');
  const [selectedSessionId, setSelectedSessionId] = useState<string>('session-150-real');
  const [useRealAI, setUseRealAI] = useState<boolean>(true);
  const [dataset150, setDataset150] = useState<any>(null);
  const [datasetSample, setDatasetSample] = useState<any>(null);
  const { locale, toggleLocale, t } = useLanguage();
  const [sessions, setSessions] = useState<SessionSummaryItem[]>(INITIAL_SESSIONS);
  const [mediaCatalog, setMediaCatalog] = useState<MediaCatalogItem[]>(MOCK_MEDIA_CATALOG);

  useEffect(() => {
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
  }, []);

  const handleUploadMedia = async (file: File): Promise<MediaCatalogItem> => {
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
    setSessions((prev) => prev.filter((s) => s.id !== id));
  };

  const handleStartSession = async (params: {
    mediaId: string;
    zoneSetId: string;
    zoneSetVersion: number;
    frameStride: number;
    useSynthetic: boolean;
  }) => {
    const newId = `session-${Date.now().toString(36)}`;
    const media = mediaCatalog.find((m) => m.id === params.mediaId);
    const zoneSet = MOCK_ZONE_SETS.find((z) => z.id === params.zoneSetId);

    const is150Media = (media?.name || '').includes('150') || params.mediaId.includes('150');
    const isSampleMedia = (media?.name || '').includes('sample') || params.mediaId.includes('sample');

    const resolvedName = media?.name ?? (is150Media ? '150.mp4 (Video Vừa Tải Lên - AI Quét Thật)' : isSampleMedia ? 'sample.mp4' : 'video.mp4');
    const resolvedDuration = media?.duration ?? (is150Media ? 57.44 : isSampleMedia ? 49.68 : 60);

    const newSession: SessionSummaryItem = {
      id: newId,
      sourceId: media?.id ?? params.mediaId,
      mediaName: resolvedName,
      duration: resolvedDuration,
      status: 'RUNNING',
      progress: 0.1,
      synthetic: params.useSynthetic,
      createdAt: new Date().toISOString().replace('T', ' ').slice(0, 19),
      zoneSetName: zoneSet?.name ?? (is150Media ? 'Khu vực Giám sát A & B' : 'Khu vực giám sát'),
      qualityBreakdown: {
        validPct: 100,
        partialPct: 0,
        unknownPct: 0,
        stalePct: 0,
      },
    };

    setSessions((prev) => [newSession, ...prev]);
    setSelectedSessionId(newId);
    setCurrentView('progress');
  };

  const { currentTime } = usePlaybackStore();

  const currentSession: SessionSummaryItem =
    sessions.find((s) => s.id === selectedSessionId) ?? sessions[0] ?? DEFAULT_SESSION;

  const is150 = Boolean(
    currentSession &&
      (currentSession.id === 'session-150-real' ||
        currentSession.sourceId === '150.mp4' ||
        currentSession.sourceId === 'media-150' ||
        currentSession.mediaName.toLowerCase().includes('150'))
  );

  const isSample = Boolean(
    currentSession &&
      (currentSession.id === 'session-yolo-real-01' ||
        currentSession.sourceId === 'sample.mp4' ||
        currentSession.sourceId === 'media-sample-01' ||
        currentSession.mediaName.toLowerCase().includes('sample'))
  );

  const isSynthetic = Boolean(currentSession?.synthetic) || (!useRealAI && !is150 && !isSample);

  // Pick dataset based on session
  const activeDataset = is150
    ? dataset150
    : isSample
      ? datasetSample
      : useRealAI
        ? (dataset150 || datasetSample)
        : null;

  const datasetFps = activeDataset?.metadata?.fps || 25;
  const datasetTotalFrames = activeDataset?.metadata?.totalFrames || (is150 ? 1436 : 1242);

  const currentFrameIdx = Math.min(
    Math.max(0, Math.round(currentTime * datasetFps)),
    datasetTotalFrames - 1
  );

  const realFrameObs = activeDataset?.frames ? activeDataset.frames[currentFrameIdx] : null;

  const activeQuality: FrameQuality = (!isSynthetic && realFrameObs)
    ? 'VALID'
    : currentTime >= 40 && currentTime <= 55
      ? 'PARTIAL'
      : 'VALID';

  const baseCountNorth = Math.max(3, Math.round(14 + Math.sin(currentTime / 4) * 4));

  // Determine videoSrc
  let videoSrc = '/150.mp4';
  if (is150) {
    videoSrc = '/150.mp4';
  } else if (isSample) {
    videoSrc = '/sample.mp4';
  } else if (currentSession?.sourceId?.startsWith('media-upload-')) {
    videoSrc = currentSession.mediaName.includes('150')
      ? '/150.mp4'
      : `/api/v1/media/${currentSession.sourceId}/stream`;
  } else if (isSynthetic) {
    videoSrc = '/sample.mp4';
  }

  const activeObservation: CrowdFrameObservation = (!isSynthetic && realFrameObs)
    ? {
        source_id: is150 ? '150.mp4' : 'sample.mp4',
        session_id: currentSession?.id || selectedSessionId,
        model_profile_id: 'yolo11n_person_detector',
        model_profile_sha256: '0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1',
        checkpoint_sha256: 'yolo11n_official_weights',
        frame_index: realFrameObs.frame_index ?? currentFrameIdx,
        media_time_s: realFrameObs.media_time_s ?? +(currentFrameIdx / datasetFps).toFixed(2),
        image_width: activeDataset?.metadata?.width || (is150 ? 1920 : 1920),
        image_height: activeDataset?.metadata?.height || (is150 ? 1440 : 1080),
        observation_valid: true,
        registration_valid: false,
        fully_observed_zones: activeDataset?.zones
          ? activeDataset.zones.map((z: any) => z.zone_id)
          : ['zone-a', 'zone-b'],
        confidence_semantics: 'RAW_MODEL_SCORE',
        quality: 'VALID',
        detections: realFrameObs.detections || [],
      }
    : {
        source_id: 'media-plaza-01',
        session_id: currentSession?.id || selectedSessionId,
        model_profile_id: 'crowd_best_local_v2',
        model_profile_sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        checkpoint_sha256: '12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc',
        frame_index: Math.round(currentTime * 25),
        media_time_s: +currentTime.toFixed(2),
        image_width: 1920,
        image_height: 1080,
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

  const activeReadings: ZoneReading[] = (!isSynthetic && realFrameObs?.zone_readings)
    ? realFrameObs.zone_readings
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

  const sampleReviewSession: SessionMetadata = (!isSynthetic && activeDataset)
    ? {
        sessionId: currentSession.id,
        sourceId: currentSession.sourceId,
        mediaName: currentSession.mediaName,
        duration: activeDataset?.metadata?.duration || currentSession.duration || 57.44,
        imageWidth: activeDataset?.metadata?.width || (is150 ? 1920 : 1920),
        imageHeight: activeDataset?.metadata?.height || (is150 ? 1440 : 1080),
        synthetic: false,
        modelProfileId: 'yolo11n_person_detector',
        modelProfileSha256: '0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1',
        checkpointSha256: 'yolo11n_official_weights',
        videoSrc: videoSrc,
        heatmapUrl: is150 ? '/media_150_heatmap.png' : '/sample_real_heatmap.png',
      }
    : {
        sessionId: currentSession.id,
        sourceId: 'media-plaza-01',
        mediaName: currentSession.mediaName.includes('plaza')
          ? currentSession.mediaName
          : 'plaza_pedestrian_cross_1080p.mp4 (Dữ liệu mẫu)',
        duration: currentSession.duration || 64.5,
        imageWidth: 1920,
        imageHeight: 1080,
        synthetic: true,
        modelProfileId: 'crowd_best_local_v2',
        modelProfileSha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        checkpointSha256: '12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc',
        videoSrc: '/sample.mp4',
      };

  const sampleZones = (!isSynthetic && activeDataset?.zones)
    ? activeDataset.zones
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
      ];

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
              zoneSets={MOCK_ZONE_SETS}
              modelProfile={MOCK_MODEL_PROFILE}
              onCreateZoneSet={() => setCurrentView('zones')}
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
            />
          )}

          {currentView === 'zones' && (
            <ZoneEditor
              imageWidth={1920}
              imageHeight={1080}
              sampleFrameUrl="/sample-frame.png"
              onSave={async () => {
                setCurrentView('wizard');
              }}
              onCancel={() => setCurrentView('sessions')}
            />
          )}

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
