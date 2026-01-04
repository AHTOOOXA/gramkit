/**
 * Configure Kubb-generated axios client with baseURL and platform-aware headers.
 * Must be called BEFORE any API requests are made.
 *
 * API URL resolution (in order):
 * 1. localhost:8003 if running on localhost (ensures same-origin for cookies)
 * 2. NEXT_PUBLIC_API_URL env var (for tunnel/production)
 * 3. /api/template-react (via nginx when accessed through domain)
 */
import { axiosInstance, setConfig } from '@kubb/plugin-client/clients/axios';
import { isMockModeEnabled } from '@tma-platform/core-react/platform';
import {
  classifyHttpError,
  classifyNetworkError,
} from '@tma-platform/core-react/errors';

interface AuthHeaders {
  initData: string;
  'Mock-Platform'?: string;
}

/**
 * Get authentication headers for API requests.
 * Extracts Telegram initData and adds mock platform header when in debug mode.
 */
function getAuthHeaders(): AuthHeaders {
  const initData =
    typeof window !== 'undefined'
      ? ((window as { Telegram?: { WebApp?: { initData?: string } } })
          .Telegram?.WebApp?.initData ?? '')
      : '';

  const isMockMode =
    process.env.NEXT_PUBLIC_DEBUG === 'true' && isMockModeEnabled();

  return {
    initData,
    ...(isMockMode ? { 'Mock-Platform': 'true' } : {}),
  };
}

/**
 * Resolve API base URL based on environment and hostname.
 *
 * Priority:
 * 1. Localhost detection (runtime) - ensures same-origin for cookies
 * 2. Explicit env var (tunnel/production)
 * 3. Relative path fallback (nginx)
 */
function resolveApiBaseUrl(): string {
  // 1. Runtime detection FIRST - localhost always uses local API (same-origin for cookies)
  if (typeof window !== 'undefined') {
    const { hostname } = window.location;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://localhost:8003';
    }
  }

  // 2. Explicit env var (tunnel/production)
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl && envUrl !== '/') {
    return envUrl;
  }

  // 3. Via nginx (domain access fallback)
  return '/api/template-react';
}

export function configureApiClient() {
  const apiBaseUrl = resolveApiBaseUrl();

  setConfig({
    baseURL: apiBaseUrl,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Also set on axiosInstance.defaults for apiFetch/getSocketOptions to read
  axiosInstance.defaults.baseURL = apiBaseUrl;

  // Enable cross-origin cookie sending (required for subdomain routing in production)
  axiosInstance.defaults.withCredentials = true;

  // Add request interceptor to Kubb's axios instance for dynamic platform-aware headers
  axiosInstance.interceptors.request.use((config) => {
    const authHeaders = getAuthHeaders();
    config.headers.set('initData', authHeaders.initData);
    if (authHeaders['Mock-Platform']) {
      config.headers.set('Mock-Platform', authHeaders['Mock-Platform']);
    }
    return config;
  });

  // Add response interceptor for error classification
  // This transforms HTTP errors into AppError instances with proper severity
  axiosInstance.interceptors.response.use(
    // Success - pass through
    (response) => response,
    // Error - classify and re-throw
    (error: unknown) => {
      // Type guard for axios error structure
      const axiosError = error as {
        response?: {
          status: number;
          data?: Record<string, unknown>;
        };
        message?: string;
      };

      // Network error (no response)
      if (!axiosError.response) {
        throw classifyNetworkError(
          error instanceof Error ? error : new Error(axiosError.message ?? 'Network error')
        );
      }

      // HTTP error - classify by status code
      const status = axiosError.response.status;
      const body = axiosError.response.data;

      throw classifyHttpError(status, body);
    }
  );
}

/**
 * Get the API base URL for use with other clients.
 */
export function getApiBaseUrl(): string {
  return axiosInstance.defaults.baseURL ?? '';
}

/**
 * Socket.io connection options type.
 */
export interface SocketOptions {
  url: string | undefined;
  options: {
    path: string;
    auth: Record<string, string>;
    withCredentials: boolean;
    transports: ('websocket' | 'polling')[];
    reconnection: boolean;
    reconnectionAttempts: number;
    reconnectionDelay: number;
  };
}

/**
 * Get socket.io connection options with correct URL, path, and auth.
 * Handles both relative paths (local dev) and absolute URLs (production).
 *
 * Usage:
 *   const { url, options } = getSocketOptions();
 *   const socket = io(url, options);
 */
export function getSocketOptions(): SocketOptions {
  const baseUrl = axiosInstance.defaults.baseURL ?? '';
  const isAbsolute = baseUrl.startsWith('http');

  // Remove trailing slash from pathname to avoid double slashes
  const pathname = isAbsolute
    ? new URL(baseUrl).pathname.replace(/\/$/, '')
    : baseUrl;

  // Get auth headers and adapt for socket.io auth format
  const authHeaders = getAuthHeaders();
  const socketAuth: Record<string, string> = {
    initData: authHeaders.initData,
    ...(authHeaders['Mock-Platform'] ? { mockPlatform: 'true' } : {}),
  };

  return {
    url: isAbsolute ? new URL(baseUrl).origin : undefined,
    options: {
      path: `${pathname}/socket.io`,
      auth: socketAuth,
      withCredentials: true,
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    },
  };
}

/**
 * Fetch wrapper with same baseURL and auth headers as axios client.
 * Use for streaming endpoints where axios doesn't work well.
 */
export function apiFetch(
  path: string,
  init?: RequestInit
): Promise<Response> {
  const baseURL = axiosInstance.defaults.baseURL ?? '';

  const headers = new Headers(init?.headers);
  const authHeaders = getAuthHeaders();
  headers.set('initData', authHeaders.initData);
  if (authHeaders['Mock-Platform']) {
    headers.set('Mock-Platform', authHeaders['Mock-Platform']);
  }

  return fetch(`${baseURL}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  });
}
