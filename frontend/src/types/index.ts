export type CameraStatus = 'online' | 'offline' | 'connecting' | 'error';
export type CameraType = 'rtsp' | 'onvif' | 'usb' | 'file' | 'http' | 'mock';

export interface CameraZone {
  name: string;
  type: 'polygon' | 'line';
  points: number[][];
  direction?: string;
  restricted: boolean;
}

export interface Camera {
  id: string;
  name: string;
  source: string;
  type: CameraType;
  enabled: boolean;
  status: CameraStatus;
  config_json: {
    stream_type: string;
    fps_cap: number;
    zones: CameraZone[];
  };
  created_at: string;
  updated_at: string;
}

export type AlertSeverity = 'info' | 'warning' | 'critical' | 'emergency';
export type AlertStatus = 'active' | 'acknowledged' | 'resolved';

export interface Alert {
  id: number;
  timestamp: string;
  camera_id: string;
  alert_type: string;
  severity: AlertSeverity;
  status: AlertStatus;
  track_id?: number;
  zone_name?: string;
  description?: string;
  metadata_json: Record<string, any>;
  acknowledged_at?: string;
  acknowledged_by?: string;
  created_at: string;
}

export interface HourlyFootfallItem {
  hour: string;
  entries: number;
  exits: number;
}

export interface FootfallMetrics {
  camera_id: string;
  date: string;
  total_entries: number;
  total_exits: number;
  hourly_trends: HourlyFootfallItem[];
}

export interface DwellZoneItem {
  zone_name: string;
  avg_dwell_seconds: number;
  max_dwell_seconds: number;
  total_visitor_count: number;
}

export interface DwellMetrics {
  camera_id: string;
  date: string;
  zones: DwellZoneItem[];
}

export interface HeatmapPoint {
  x: number;
  y: number;
  intensity: number;
}

export interface HeatmapData {
  camera_id: string;
  resolution: number[];
  points: HeatmapPoint[];
}

export interface SystemStatus {
  status: string;
  uptime: number;
  version: string;
}

export interface HardwareInfo {
  os: string;
  architecture: string;
  python_version: string;
  onnx_version: string;
  available_providers: string[];
  preferred_backend: string;
}

export interface BoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface TrackedObject {
  track_id: number;
  class_id: number;
  class_name: string;
  confidence: number;
  box: BoundingBox;
  zone_name?: string;
  role: string;
}

export interface WebSocketMessage {
  type: string;
  timestamp: number;
  camera_id: string;
  data: any;
}
