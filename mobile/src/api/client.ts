import { ApiError, mapHttpStatus } from './errors';
import { isApiConfigured, resolveApiConfig } from './config';
import type { ApiClientConfig, ApiSuccessEnvelope } from './types';

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export interface RequestOptions {
  method?: HttpMethod;
  path: string;
  body?: unknown;
  headers?: Record<string, string>;
  /** When true, body is FormData and Content-Type is left to the runtime. */
  formData?: FormData;
  signal?: AbortSignal;
}

export class FoxApiClient {
  private config: ApiClientConfig;

  constructor(config?: Partial<ApiClientConfig>) {
    this.config = resolveApiConfig(config);
  }

  getConfig(): ApiClientConfig {
    return this.config;
  }

  isConfigured(): boolean {
    return isApiConfigured(this.config);
  }

  async request<T>(options: RequestOptions): Promise<T> {
    if (!this.isConfigured()) {
      throw new ApiError(
        'not_configured',
        'FOX API base URL is not configured. The mobile app is not connected to a production backend.'
      );
    }

    const headers: Record<string, string> = {
      Accept: 'application/json',
      ...(options.headers ?? {}),
    };

    const token = await this.resolveToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    let body: BodyInit | undefined;
    if (options.formData) {
      body = options.formData;
    } else if (options.body !== undefined) {
      headers['Content-Type'] = 'application/json';
      body = JSON.stringify(options.body);
    }

    const controller = new AbortController();
    const timeout = setTimeout(
      () => controller.abort(),
      this.config.timeoutMs ?? 30_000
    );
    const signal = options.signal ?? controller.signal;

    try {
      const response = await fetch(`${this.config.baseUrl}${options.path}`, {
        method: options.method ?? 'GET',
        headers,
        body,
        signal,
      });

      const text = await response.text();
      let parsed: unknown = null;
      if (text) {
        try {
          parsed = JSON.parse(text);
        } catch {
          parsed = { message: text };
        }
      }

      if (!response.ok) {
        const msg =
          parsed &&
          typeof parsed === 'object' &&
          'message' in parsed &&
          typeof (parsed as { message: unknown }).message === 'string'
            ? (parsed as { message: string }).message
            : undefined;
        throw mapHttpStatus(response.status, msg);
      }

      return parsed as T;
    } catch (err) {
      if (err instanceof ApiError) throw err;
      if (err instanceof Error && err.name === 'AbortError') {
        throw new ApiError('timeout', 'Request timed out');
      }
      throw new ApiError(
        'network',
        err instanceof Error ? err.message : 'Network request failed'
      );
    } finally {
      clearTimeout(timeout);
    }
  }

  async requestData<T>(options: RequestOptions): Promise<T> {
    const envelope = await this.request<ApiSuccessEnvelope<T>>(options);
    if (envelope && typeof envelope === 'object' && 'data' in envelope) {
      return envelope.data;
    }
    return envelope as unknown as T;
  }

  private async resolveToken(): Promise<string | null> {
    const getter = this.config.getAccessToken;
    if (!getter) return null;
    return getter();
  }
}

let sharedClient: FoxApiClient | null = null;

export function getApiClient(config?: Partial<ApiClientConfig>): FoxApiClient {
  if (config) {
    sharedClient = new FoxApiClient(config);
    return sharedClient;
  }
  if (!sharedClient) {
    sharedClient = new FoxApiClient();
  }
  return sharedClient;
}

export function resetApiClient(): void {
  sharedClient = null;
}
