/**
 * Configure Kubb-generated axios client with baseURL and platform-aware headers.
 *
 * This must be called BEFORE any API requests are made.
 *
 * API URL resolution (in order):
 * 1. localhost:8002 if running on localhost (direct backend, CORS enabled in debug)
 * 2. VITE_API_HOST env var (for tunnel/production)
 * 3. /api/template (via nginx when accessed through domain)
 *
 * IMPORTANT: Configures critical authentication headers via axios interceptor:
 * - initData: Telegram WebApp initialization data for authentication
 * - Mock-Platform: Enables mock user authentication in debug mode
 *
 * ERROR HANDLING: Response interceptor classifies errors into ApiError instances
 * with proper retry classification for TanStack Query retry logic.
 */
import { setConfig, axiosInstance } from '@kubb/plugin-client/clients/axios';
import { classifyHttpError, classifyNetworkError } from '@core/errors';

const STORAGE_KEY = 'telegram-platform-mock';

/**
 * Resolve API base URL based on environment and hostname.
 *
 * Priority:
 * 1. Localhost detection (runtime) - ensures same-origin for cookies
 * 2. Explicit env var (tunnel/production)
 * 3. Relative path fallback (nginx)
 */
function resolveApiBaseUrl(): string {
  // 1. Runtime detection FIRST - localhost always uses direct backend (CORS enabled in debug mode)
  if (typeof window !== 'undefined') {
    const { hostname } = window.location;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://localhost:8002';
    }
  }

  // 2. Explicit env var (tunnel/production)
  const envUrl = import.meta.env.VITE_API_HOST;
  if (envUrl && envUrl !== '/') {
    return envUrl;
  }

  // 3. Via nginx (domain access fallback)
  return '/api/template';
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
    // Get initData from Telegram WebApp (set by platform or mock)
    const initData = typeof window !== 'undefined'
      ? (window as { Telegram?: { WebApp?: { initData?: string } } }).Telegram?.WebApp?.initData ?? ''
      : '';

    // Check if mock mode is enabled (debug mode only)
    let isMockMode = false;
    if (import.meta.env.VITE_DEBUG === 'true' && typeof window !== 'undefined') {
      try {
        isMockMode = localStorage.getItem(STORAGE_KEY) === 'true';
      } catch {
        isMockMode = false;
      }
    }

    // Set initData header (required for all Telegram authentication)
    config.headers.set('initData', initData);

    // Add mock platform header when in mock mode
    if (isMockMode) {
      config.headers.set('Mock-Platform', 'true');
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

  // Get auth data
  const initData =
    typeof window !== 'undefined'
      ? ((window as { Telegram?: { WebApp?: { initData?: string } } })
          .Telegram?.WebApp?.initData ?? '')
      : '';
  let isMockMode = false;
  if (import.meta.env.VITE_DEBUG === 'true' && typeof window !== 'undefined') {
    try {
      isMockMode = localStorage.getItem(STORAGE_KEY) === 'true';
    } catch {
      isMockMode = false;
    }
  }

  // Remove trailing slash from pathname to avoid double slashes
  const pathname = isAbsolute
    ? new URL(baseUrl).pathname.replace(/\/$/, '')
    : baseUrl;

  return {
    url: isAbsolute ? new URL(baseUrl).origin : undefined,
    options: {
      path: `${pathname}/socket.io`,
      auth: {
        initData,
        ...(isMockMode ? { mockPlatform: 'true' } : {}),
      },
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

  // Get initData from Telegram WebApp
  const initData =
    typeof window !== 'undefined'
      ? ((window as { Telegram?: { WebApp?: { initData?: string } } })
          .Telegram?.WebApp?.initData ?? '')
      : '';

  // Check if mock mode is enabled
  let isMockMode = false;
  if (import.meta.env.VITE_DEBUG === 'true' && typeof window !== 'undefined') {
    try {
      isMockMode = localStorage.getItem(STORAGE_KEY) === 'true';
    } catch {
      isMockMode = false;
    }
  }

  const headers = new Headers(init?.headers);
  headers.set('initData', initData);
  if (isMockMode) {
    headers.set('Mock-Platform', 'true');
  }

  return fetch(`${baseURL}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  });
}
