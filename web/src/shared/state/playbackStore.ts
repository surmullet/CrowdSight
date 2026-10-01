import { create } from 'zustand';
import type { CrowdFrameObservation, ZoneReading } from '@/shared/types/domain';

interface PlaybackState {
  currentTime: number;
  duration: number;
  isPlaying: boolean;
  playbackRate: number;
  showBoxes: boolean;
  showZones: boolean;
  showHeatmap: boolean;
  heatmapOpacity: number;
  selectedZoneId: string | null;
  activeObservation: CrowdFrameObservation | null;
  activeReadings: ZoneReading[];

  // Actions
  setCurrentTime: (time: number) => void;
  setDuration: (duration: number) => void;
  setIsPlaying: (playing: boolean) => void;
  setPlaybackRate: (rate: number) => void;
  toggleBoxes: () => void;
  toggleZones: () => void;
  toggleHeatmap: () => void;
  setHeatmapOpacity: (opacity: number) => void;
  setSelectedZoneId: (zoneId: string | null) => void;
  setActiveObservation: (obs: CrowdFrameObservation | null) => void;
  setActiveReadings: (readings: ZoneReading[]) => void;
}

export const usePlaybackStore = create<PlaybackState>((set) => ({
  currentTime: 0,
  duration: 0,
  isPlaying: false,
  playbackRate: 1.0,
  showBoxes: true,
  showZones: true,
  showHeatmap: false,
  heatmapOpacity: 0.6,
  selectedZoneId: null,
  activeObservation: null,
  activeReadings: [],

  setCurrentTime: (time) => set({ currentTime: Math.max(0, time) }),
  setDuration: (duration) => set({ duration: Math.max(0, duration) }),
  setIsPlaying: (isPlaying) => set({ isPlaying }),
  setPlaybackRate: (playbackRate) => set({ playbackRate }),
  toggleBoxes: () => set((state) => ({ showBoxes: !state.showBoxes })),
  toggleZones: () => set((state) => ({ showZones: !state.showZones })),
  toggleHeatmap: () => set((state) => ({ showHeatmap: !state.showHeatmap })),
  setHeatmapOpacity: (heatmapOpacity) => set({ heatmapOpacity: Math.min(1, Math.max(0, heatmapOpacity)) }),
  setSelectedZoneId: (selectedZoneId) => set({ selectedZoneId }),
  setActiveObservation: (activeObservation) => set({ activeObservation }),
  setActiveReadings: (activeReadings) => set({ activeReadings }),
}));
