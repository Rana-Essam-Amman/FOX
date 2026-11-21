import type { ApiClientConfig } from './types';

/**
 * Resolve client config from public environment only.
 * Never place provider secrets or shared backend keys here.
 * EXPO_PUBLIC_FOX_API_URL is optional; empty means not connected.
 */
export function resolveApiConfig(
  overrides: Partial<ApiClientConfig> = {}
): ApiClientConfig {
  const fromEnv =
    (typeof process !== 'undefined' &&
      process.env &&
      process.env.EXPO_PUBLIC_FOX_API_URL) ||
    '';

  return {
    baseUrl: (overrides.baseUrl ?? fromEnv).replace(/\/$/, ''),
    timeoutMs: overrides.timeoutMs ?? 30_000,
    getAccessToken: overrides.getAccessToken,
  };
}

export function isApiConfigured(config: ApiClientConfig): boolean {
  return Boolean(config.baseUrl && config.baseUrl.length > 0);
}
