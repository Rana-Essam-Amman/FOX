/** Typed contracts for the FOX mobile API client.
 *  Shapes mirror the FastAPI gateway surface without embedding secrets.
 */

export type TaskStatus =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type TaskKind = 'video' | 'subtitle' | 'audio' | 'image' | 'tts' | 'stt';

export interface ApiSuccessEnvelope<T> {
  status: number;
  message?: string;
  data: T;
}

export interface CreateTaskRequest {
  kind: TaskKind;
  prompt: string;
  duration?: '15s' | '30s' | '60s';
  style?: 'cinematic' | 'dynamic' | 'minimal';
  aspect?: '16:9' | '9:16' | '1:1';
  language?: string;
  /** Server-side material id after upload; never a local temp URI. */
  materialId?: string;
}

export interface CreateTaskResult {
  taskId: string;
}

export interface TaskStatusResult {
  taskId: string;
  status: TaskStatus;
  progress?: number;
  errorMessage?: string;
  resultUrl?: string;
  resultUrls?: string[];
}

export interface UploadResult {
  materialId: string;
  contentType?: string;
  size?: number;
}

export interface AuthTokens {
  /** Bearer or opaque session token issued by the gateway. */
  accessToken: string;
  refreshToken?: string;
  expiresAt?: number;
}

export interface ApiClientConfig {
  /** Base URL of the FOX gateway. Empty means offline / not connected. */
  baseUrl: string;
  /** Optional request timeout in milliseconds. */
  timeoutMs?: number;
  /** Provider of auth headers; never stores provider API keys. */
  getAccessToken?: () => Promise<string | null> | string | null;
}
