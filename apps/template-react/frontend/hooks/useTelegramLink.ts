'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { getCurrentUserUsersMeGetQueryKey } from '@/src/gen/hooks';
import { getApiBaseUrl } from '@/config/kubb-config';

interface StartResponse {
  link_token: string;
  bot_url: string;
  expires_in: number;
}

interface CheckResponse {
  status: 'pending' | 'completed' | 'expired' | 'error';
  telegram_id?: number;
  telegram_username?: string;
  error?: string;
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
 * Hook for linking Telegram account to an existing user (requires authentication).
 *
 * Uses endpoints:
 * - POST /auth/link/telegram/start
 * - GET /auth/link/telegram/poll
 */
export function useTelegramLink() {
  const queryClient = useQueryClient();

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
      const response = await fetchWithCredentials('/auth/link/telegram/start', {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to start authentication');
      }

      const data = (await response.json()) as StartResponse;
      tokenRef.current = data.link_token;
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
            `/auth/link/telegram/poll?token=${tokenRef.current ?? ''}`,
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

          const checkData = (await checkResponse.json()) as CheckResponse;
          if (checkData.status === 'completed') {
            stop();
            await queryClient.invalidateQueries({
              queryKey: getCurrentUserUsersMeGetQueryKey(),
            });
          } else if (checkData.status === 'error') {
            stop();
            // Map error codes to user-friendly messages
            const errorMessages: Record<string, string> = {
              telegram_already_used: 'This Telegram account is already linked to another user.',
            };
            setError(errorMessages[checkData.error ?? ''] ?? 'Linking failed.');
          }
        } catch {
          // Network error, continue polling
        }
      };

      pollRef.current = setInterval(() => {
        void poll();
      }, 3000);
    } catch {
      setError('Failed to start.');
    } finally {
      setIsStarting(false);
    }
  }, [queryClient, stop]);

  useEffect(() => () => { stop(); }, [stop]);

  return { isStarting, isPolling, error, botUrl, start, stop, reset, openTelegram };
}
