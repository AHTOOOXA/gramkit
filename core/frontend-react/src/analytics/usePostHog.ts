import { useCallback } from 'react';
import posthog from 'posthog-js';

export interface UsePostHogReturn {
  capture: (event: string, properties?: Record<string, any>) => void;
  identify: (userId: string, properties?: Record<string, any>) => void;
  reset: () => void;
}

export function usePostHog(): UsePostHogReturn {
  const capture = useCallback(
    (event: string, properties?: Record<string, any>) => {
      if (typeof window !== 'undefined') {
        posthog.capture(event, properties);
      }
    },
    []
  );

  const identify = useCallback(
    (userId: string, properties?: Record<string, any>) => {
      if (typeof window !== 'undefined') {
        posthog.identify(userId, properties);
      }
    },
    []
  );

  const reset = useCallback(() => {
    if (typeof window !== 'undefined') {
      posthog.reset();
    }
  }, []);

  return {
    capture,
    identify,
    reset,
  };
}

/**
 * Initialize PostHog (call once in app initialization)
 */
export function initPostHog(apiKey: string, options?: Record<string, any>): void {
  if (typeof window !== 'undefined' && apiKey) {
    posthog.init(apiKey, {
      api_host: 'https://app.posthog.com',
      ...options,
    });
  }
}
