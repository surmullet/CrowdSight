/**
 * Core domain types and discriminated union ensuring zero is never confused with missing data.
 */

export type FrameQuality = 'VALID' | 'PARTIAL' | 'UNKNOWN' | 'STALE';

/**
 * Invariant: ZoneReading is a discriminated union.
 * When status is not 'COUNTED', `count` property does NOT exist on the type,
 * making it impossible for UI code to accidentally display a count or default to zero.
 */
export type ZoneReading =
  | {
      status: 'COUNTED';
      count: number;
      zoneId: string;
      zoneName: string;
      isPartialObservation?: boolean;
    }
  | {
      status: 'NOT_FULLY_OBSERVED';
      zoneId: string;
      zoneName: string;
    }
  | {
      status: 'UNKNOWN';
      zoneId: string;
      zoneName: string;
      reasonCode?: string;
    }
  | {
      status: 'STALE';
      zoneId: string;
      zoneName: string;
      staleGapSeconds: number;
    };

export interface DetectionAnchor {
  x: number; // Normalized bottom-centre [0, 1]
  y: number; // Normalized bottom-centre [0, 1]
  confidence: number; // Raw model score [0, 1]
  bbox_xyxy: [number, number, number, number]; // Source pixel bounding box [x1, y1, x2, y2]
  track_id?: number | null;
}

export interface CrowdFrameObservation {
  source_id: string;
  session_id: string;
  model_profile_id: string;
  model_profile_sha256: string;
  checkpoint_sha256: string;
  tracker_config_sha256?: string | null;
  frame_index: number;
  media_time_s: number;
  captured_at?: string | null;
  image_width: number;
  image_height: number;
  observation_valid: boolean;
  registration_valid: boolean;
  fully_observed_zones: string[];
  confidence_semantics: 'RAW_MODEL_SCORE';
  quality: FrameQuality;
  detections: DetectionAnchor[];
}

export interface ModelApplicability {
  profile_id: string;
  model_family: string;
  checkpoint_sha256: string;
  checkpoint_available: boolean;
  applicability_status: string;
  operational_alerts_allowed: boolean;
  experimental_warning: string;
}
