export type ApiErrorCode =
  | 'not_configured'
  | 'network'
  | 'timeout'
  | 'unauthorized'
  | 'forbidden'
  | 'not_found'
  | 'validation'
  | 'rate_limited'
  | 'server'
  | 'unknown';

export class ApiError extends Error {
  readonly code: ApiErrorCode;
  readonly status: number | null;
  readonly details?: unknown;

  constructor(
    code: ApiErrorCode,
    message: string,
    status: number | null = null,
    details?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

export function mapHttpStatus(status: number, bodyMessage?: string): ApiError {
  const message = bodyMessage || `Request failed with status ${status}`;
  if (status === 401) return new ApiError('unauthorized', message, status);
  if (status === 403) return new ApiError('forbidden', message, status);
  if (status === 404) return new ApiError('not_found', message, status);
  if (status === 422 || status === 400) return new ApiError('validation', message, status);
  if (status === 429) return new ApiError('rate_limited', message, status);
  if (status >= 500) return new ApiError('server', message, status);
  return new ApiError('unknown', message, status);
}
