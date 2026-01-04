import { ref, onUnmounted } from 'vue';
import { useAppInit } from './useAppInit';
import { startDeeplinkLoginAuthLoginTelegramDeeplinkStartPost, pollDeeplinkLoginAuthLoginTelegramDeeplinkPollGet } from '@/gen/client';

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

  const isStarting = ref(false);
  const isPolling = ref(false);
  const error = ref<string | null>(null);
  const botUrl = ref<string | null>(null);

  let pollInterval: ReturnType<typeof setInterval> | null = null;
  let currentToken: string | null = null;

  const stop = () => {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
    isPolling.value = false;
    currentToken = null;
  };

  const reset = () => {
    stop();
    botUrl.value = null;
    error.value = null;
  };

  const openTelegram = () => {
    if (botUrl.value) {
      window.open(botUrl.value, '_blank');
    }
  };

  const start = async () => {
    isStarting.value = true;
    error.value = null;

    try {
      const data = await startDeeplinkLoginAuthLoginTelegramDeeplinkStartPost();
      currentToken = data.token;
      botUrl.value = data.bot_url;
      window.open(data.bot_url, '_blank');

      isPolling.value = true;
      let attempts = 0;

      const poll = async () => {
        attempts++;
        if (attempts > 60) {
          stop();
          error.value = 'Login timed out.';
          return;
        }

        try {
          const checkData = await pollDeeplinkLoginAuthLoginTelegramDeeplinkPollGet({
            token: currentToken ?? ''
          });

          if (checkData.status === 'verified') {
            stop();
            // Trigger app re-initialization (handles /process_start, PostHog, cache update)
            reinitialize();
          }
        } catch (err: unknown) {
          // Handle 410 status (expired)
          const axiosError = err as { response?: { status?: number } };
          if (axiosError?.response?.status === 410) {
            stop();
            error.value = 'Login link expired.';
            return;
          }
          // Network error or pending status, continue polling
        }
      };

      pollInterval = setInterval(() => {
        void poll();
      }, 3000);
    } catch {
      error.value = 'Failed to start login.';
    } finally {
      isStarting.value = false;
    }
  };

  onUnmounted(() => stop());

  return {
    isStarting,
    isPolling,
    error,
    botUrl,
    start,
    stop,
    reset,
    openTelegram,
  };
}
