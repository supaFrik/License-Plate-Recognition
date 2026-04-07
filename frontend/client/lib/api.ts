export type UserRole = "ADMIN" | "OPERATOR";
export type VehicleStatus = "CITIZEN" | "BANNED";
export type VisitorType = "CITIZEN" | "GUEST" | "BANNED";

export interface AuthUser {
  id: number;
  email: string;
  role: UserRole;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
}

export interface Camera {
  id: number;
  location_name: string;
  status: string;
}

export interface CameraListResponse {
  items: Camera[];
}

export interface Vehicle {
  id: number;
  plate_number: string;
  owner_name: string;
  status: VehicleStatus;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
}

export interface VehicleListResponse {
  items: Vehicle[];
  pagination: PaginationMeta;
}

export interface Detection {
  id: number;
  camera_id: number;
  camera_name: string;
  plate_number: string;
  confidence: number;
  visitor_type: VisitorType;
  input_kind: "image" | "video";
  capture_url?: string | null;
  timestamp: string;
}

export interface DetectionListResponse {
  items: Detection[];
  pagination: PaginationMeta;
}

export interface DetectionLiveResponse {
  items: Detection[];
  latest_id: number;
}

export interface PlateBoundingBox {
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
}

export interface DetectionRecognizeResponse {
  filename: string;
  content_type?: string | null;
  input_kind: "image" | "video";
  detected: boolean;
  plate_number?: string | null;
  confidence?: number | null;
  plate_type?: string | null;
  bbox?: PlateBoundingBox | null;
  image_width: number;
  image_height: number;
  sampled_frames: number;
  analyzed_frames: number;
  selected_frame_index?: number | null;
  validation_note?: string | null;
  processing_ms: number;
  saved_to_db: boolean;
  detection?: Detection | null;
}

export interface DetectionRecognizeBatchResponse {
  items: DetectionRecognizeResponse[];
  total_files: number;
  detected_count: number;
  processing_ms: number;
}

const rawBaseUrl =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  "http://127.0.0.1:8000";

export const API_BASE_URL = rawBaseUrl.replace(/\/$/, "");

let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function clearAccessToken() {
  accessToken = null;
}

export function getApiUrl(path: string) {
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

export function getMediaUrl(path: string | null | undefined) {
  if (!path) {
    return null;
  }
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  return getApiUrl(path);
}

export async function apiFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  if (accessToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  return fetch(getApiUrl(path), {
    ...init,
    headers,
    credentials: "include",
  });
}

export async function readApiError(response: Response) {
  try {
    const payload = await response.json();
    if (typeof payload?.detail === "string") {
      return payload.detail;
    }
  } catch {
    return response.statusText || "Request failed.";
  }

  return response.statusText || "Request failed.";
}
