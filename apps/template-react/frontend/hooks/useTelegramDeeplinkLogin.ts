'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

import { useAppInit } from '@/providers';
import { getApiBaseUrl } from '@/config/kubb-config';

interface StartResponse {
  token: string;
  bot_url: string;
  expires_in: number;
}

interface PollResponse {
  status: 'pending' | 'verified' | 'expired';
  user_id?: number;
}

async function fetchWithCredentials(url: string, options: RequestInit = {}): Promise<Response> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (options.headers) {
    const optHeaders = options.headers as Record<string, string>;
    Object.assign(headers, optHeaders);
  }

  return fetch(`${getApiBaseUrl()}${url}`, {
    ...options,
    credentials: 'include',
    headers,
  });
}

/**
 * Hook for Telegram deep link LOGIN flow (for unauthenticated users).
 *
 * Flow:
 * 1. Call start() to get bot URL with auth token
 * 2. User opens Telegram bot and confirms
 * 3. Poll for completion, session cookie is set on success
 * 4. Triggers app re-initialization via useAppInit().reinitialize()
 *
 * Uses endpoints:
 * - POST /auth/login/telegram/deeplink/start
 * - GET /auth/login/telegram/deeplink/poll
 */
export function useTelegramDeeplinkLogin() {
  const { reinitialize } = useAppInit();

  const [isStarting, setIsStarting] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [botUrl, setBotUrl] = useState<string | null>(null);

  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const tokenRef = useRef<string | null>(null);

  const stop = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    setIsPolling(false);
    tokenRef.current = null;
  }, []);

  const reset = useCallback(() => {
    stop();
    setBotUrl(null);
    setError(null);
  }, [stop]);

  const openTelegram = useCallback(() => {
    if (botUrl) {
      window.open(botUrl, '_blank');
    }
  }, [botUrl]);

  const start = useCallback(async () => {
    setIsStarting(true);
    setError(null);

    try {
      const response = await fetchWithCredentials('/auth/login/telegram/deeplink/start', {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to start login');
      }

      const data = (await response.json()) as StartResponse;
      tokenRef.current = data.token;
      setBotUrl(data.bot_url);
      window.open(data.bot_url, '_blank');

      setIsPolling(true);
      let attempts = 0;

      const poll = async (): Promise<void> => {
        attempts++;
        if (attempts > 60) {
          stop();
          setError('Login timed out.');
          return;
        }

        try {
          const checkResponse = await fetchWithCredentials(
            `/auth/login/telegram/deeplink/poll?token=${tokenRef.current ?? ''}`,
            { method: 'GET' }
          );

          if (checkResponse.status === 410) {
            stop();
            setError('Login link expired.');
            return;
          }

          if (!checkResponse.ok) {
            return;
          }

          const checkData = (await checkResponse.json()) as PollResponse;
          if (checkData.status === 'verified') {
            stop();
            // Trigger app re-initialization (handles /process_start, PostHog, cache update)
            reinitialize();
          }
        } catch {
          // Network error, continue polling
        }
      };

      pollRef.current = setInterval(() => {
        void poll();
      }, 3000);
    } catch {
      setError('Failed to start login.');
    } finally {
      setIsStarting(false);
    }
  }, [reinitialize, stop]);

  useEffect(() => () => { stop(); }, [stop]);

  return { isStarting, isPolling, error, botUrl, start, stop, reset, openTelegram };
}
