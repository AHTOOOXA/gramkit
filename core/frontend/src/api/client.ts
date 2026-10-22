import createClient from 'openapi-fetch';
import type { paths } from '@schema/api';
import { usePlatform } from '@core/platform';
import { usePlatformMock } from '@core/platform';

// Validate required environment variables
const API_HOST = import.meta.env.VITE_API_HOST;
if (!API_HOST) {
  throw new Error(
    'VITE_API_HOST environment variable is required.\n' +
    'Set it in your .env file, for example: VITE_API_HOST=http://localhost:3000'
  );
}

// Get platform-specific configuration
function getPlatformConfig() {
  const platform = usePlatform();
  const platformMock = usePlatformMock();

  // The Mock-Platform header gates the backend's mock-user auth, so it's tied to
  // login-as (which user), NOT TG-platform mock (telegram vs web).
  const isUserMock = import.meta.env.VITE_DEBUG === 'true' && platformMock.isUserMockEnabled.value;

  const headers: Record<string, string> = {
    initData: platform.webAppInitData || '',
  };

  // Tell the backend to accept the mock user carried in initData.
  if (isUserMock) {
    headers['Mock-Platform'] = 'true';
  }

  return {
    headers,
    // Only include credentials for web platform, not for Telegram Mini App
    credentials: platform.isWeb ? ('include' as RequestCredentials) : ('omit' as RequestCredentials),
  };
}

// openapi-fetch client for typed API calls
const apiClient = createClient<paths>({
  baseUrl: API_HOST,
  ...getPlatformConfig(),
});

// Custom fetch wrapper for endpoints not in OpenAPI schema or with special requirements
export interface ApiFetchOptions extends Omit<RequestInit, 'headers'> {
  headers?: Record<string, string>;
}

export async function apiFetch(url: string, options: ApiFetchOptions = {}): Promise<Response> {
  // Construct full URL if relative path provided
  const fullUrl = url.startsWith('http') ? url : `${API_HOST}${url.startsWith('/') ? url : `/${url}`}`;

  // Get platform configuration dynamically
  const platformConfig = getPlatformConfig();

  const headers = {
    ...platformConfig.headers,
    ...options.headers,
  };

  // Make request with platform-specific credentials configuration
  return fetch(fullUrl, {
    credentials: platformConfig.credentials,
    ...options,
    headers,
  });
}

export default apiClient;
