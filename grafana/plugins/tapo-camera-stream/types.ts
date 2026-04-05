/**
 * Types for the Tapo Camera Stream Panel Plugin
 */

export interface SimpleOptions {
  /**
   * URL of the camera stream
   * Can be RTSP, RTMP, HLS, WebRTC, or MJPEG
   */
  streamUrl: string;

  /**
   * Type of video stream
   */
  streamType: 'hls' | 'rtsp' | 'rtmp' | 'webrtc' | 'mjpeg';

  /**
   * Whether to use authentication for the stream
   */
  useAuth: boolean;

  /**
   * Username for authentication
   */
  username: string;

  /**
   * Password for authentication
   */
  password: string;

  /**
   * Whether to show playback controls
   */
  showControls: boolean;

  /**
   * Whether to automatically start playing the stream
   */
  autoPlay: boolean;

  /**
   * Whether to show PTZ controls
   */
  showPtzControls: boolean;

  /**
   * Whether to mute the audio
   */
  muted: boolean;

  /**
   * Maximum width of the video player (0 for auto)
   */
  maxWidth: number;
}

/**
 * Data point from the query
 */
export interface DataPoint {
  time: number | string;
  value: number;
}

/**
 * Field configuration
 */
export interface FieldConfig {
  title?: string;
  unit?: string;
  decimals?: number;
  min?: number;
  max?: number;
}

/**
 * Panel data structure
 */
export interface PanelData {
  series: Array<{
    name: string;
    fields: Array<{
      name: string;
      type: string;
      values: any[];
      config: FieldConfig;
    }>;
  }>;
  state?: any;
  timeRange?: {
    from: number;
    to: number;
  };
}

/**
 * Camera status
 */
export interface CameraStatus {
  isOnline: boolean;
  lastSeen?: string;
  resolution?: {
    width: number;
    height: number;
  };
  bitrate?: number;
  codec?: string;
  fps?: number;
}

/**
 * PTZ position
 */
export interface PTZPosition {
  pan: number;
  tilt: number;
  zoom: number;
}

/**
 * Camera capabilities
 */
export interface CameraCapabilities {
  ptz: boolean;
  audio: boolean;
  motionDetection: boolean;
  nightVision: boolean;
  zoom: boolean;
  focus: boolean;
  presets: boolean;
  privacyMask: boolean;
}

/**
 * Camera information
 */
export interface CameraInfo {
  id: string;
  name: string;
  model: string;
  firmware: string;
  manufacturer: string;
  serialNumber: string;
  ipAddress: string;
  macAddress: string;
  capabilities: CameraCapabilities;
  status: CameraStatus;
  ptzPosition?: PTZPosition;
  presets?: Array<{
    id: number;
    name: string;
    position: PTZPosition;
    thumbnailUrl?: string;
  }>;
}
