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
    name: 'Khu vực quảng trường trung tâm',
    version: 1,
    zoneCount: 2,
  },
  {
    id: 'zs-gates',
    name: 'Cổng đón trả khách',
    version: 2,
    zoneCount: 3,
  },
];

const MOCK_MODEL_PROFILE: ModelProfileInfo = {
  profileId: 'crowd_best_local_v2',
  profileSha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  checkpointSha256: '12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc',
  applicabilityStatus: 'EXPERIMENTAL_NO_APPROVAL',
  operationalAlertsAllowed: false,
};

const INITIAL_SESSIONS: SessionSummaryItem[] = [
  {
    id: 'session-demo-01',
    sourceId: 'media-plaza-01',
    mediaName: 'plaza_pedestrian_cross_1080p.mp4',
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

export const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<AppView>('sessions');
  const [selectedSessionId, setSelectedSessionId] = useState<string>('session-demo-01');
  const [locale, setLocale] = useState<'vi' | 'en'>('vi');
  const [sessions, setSessions] = useState<SessionSummaryItem[]>(INITIAL_SESSIONS);
  const [mediaCatalog, setMediaCatalog] = useState<MediaCatalogItem[]>(MOCK_MEDIA_CATALOG);

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
    const media = MOCK_MEDIA_CATALOG.find((m) => m.id === params.mediaId);
    const zoneSet = MOCK_ZONE_SETS.find((z) => z.id === params.zoneSetId);

    const newSession: SessionSummaryItem = {
      id: newId,
      sourceId: params.mediaId,
      mediaName: media?.name ?? 'unknown.mp4',
      duration: media?.duration ?? 60,
      status: 'RUNNING',
      progress: 0.1,
      synthetic: params.useSynthetic,
      createdAt: new Date().toISOString().replace('T', ' ').slice(0, 19),
      zoneSetName: zoneSet?.name,
    };

    setSessions((prev) => [newSession, ...prev]);
    setSelectedSessionId(newId);
    setCurrentView('progress');
  };

  const { currentTime } = usePlaybackStore();

  const activeQuality: FrameQuality =
    currentTime >= 40 && currentTime <= 55 ? 'PARTIAL' : 'VALID';

  const baseCountNorth = Math.max(3, Math.round(14 + Math.sin(currentTime / 4) * 4));

  const activeObservation: CrowdFrameObservation = {
    source_id: 'media-plaza-01',
    session_id: selectedSessionId,
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

  const activeReadings: ZoneReading[] = [
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
    const csvContent =
      'data:text/csv;charset=utf-8,media_time_s,frame_index,zone_id,zone_name,visible_count,quality\n' +
      `${currentTime.toFixed(2)},${Math.round(currentTime * 25)},zone-north,Khu vực Bắc (Quảng trường),${baseCountNorth},${activeQuality}\n` +
      `${currentTime.toFixed(2)},${Math.round(currentTime * 25)},zone-south,Khu vực Nam (Lối vào),0,${activeQuality}\n`;
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `crowdsight_${selectedSessionId}.csv`);
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
    link.setAttribute('download', `crowdsight_${selectedSessionId}_v1.jsonl`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const sampleReviewSession: SessionMetadata = {
    sessionId: selectedSessionId,
    sourceId: 'media-plaza-01',
    mediaName: 'plaza_pedestrian_cross_1080p.mp4',
    duration: 64.5,
    imageWidth: 1920,
    imageHeight: 1080,
    synthetic: true,
    modelProfileId: 'crowd_best_local_v2',
    modelProfileSha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    checkpointSha256: '12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc',
    videoSrc: '/sample.mp4',
  };

  const sampleZones = [
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
                  Giám sát đám đông video
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
                <span>Thư viện</span>
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
                <span>Tạo phiên</span>
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
                <span>Soạn vùng</span>
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
                <span>Mô hình</span>
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
              onClick={() => setLocale(locale === 'vi' ? 'en' : 'vi')}
              className="flex items-center gap-1 px-2 py-1 rounded text-xs text-brand-text-muted hover:text-brand-text-primary hover:bg-brand-surface transition-colors"
              title="Đổi ngôn ngữ giao diện"
            >
              <Languages className="w-3.5 h-3.5" />
              <span className="font-mono text-[10px] uppercase font-medium">{locale}</span>
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
              onComplete={() => setCurrentView('review')}
              onOpenPartialResults={() => setCurrentView('review')}
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
                { startTime: 55, endTime: 64.5, quality: 'VALID' },
              ]}
              zoneTrends={[
                {
                  zoneId: 'zone-north',
                  name: 'Khu vực Bắc',
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
              ]}
              peaks={[
                { time: 20, count: 18, zoneId: 'zone-north', label: 'Đỉnh lúc 00:20' },
              ]}
              initialNotes={[
                { id: 'n1', time: 10, text: 'Bắt đầu có nhóm người di chuyển từ cổng vào.' },
              ]}
              onExportCsv={handleExportCsv}
              onExportJsonl={handleExportJsonl}
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

export default App;
