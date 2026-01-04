import { ref, onUnmounted, type Ref } from 'vue';
import { useQueryClient } from '@tanstack/vue-query';
import { useStartLinkAuthLinkTelegramStartPost } from '@/gen/hooks/useStartLinkAuthLinkTelegramStartPost';
import { getCurrentUserUsersMeGetQueryKey } from '@/gen/hooks/useGetCurrentUserUsersMeGet';
import { apiFetch } from '@/config/kubb-config';
import type { TelegramLinkStatusResponse } from '@/gen/models/TelegramLinkStatusResponse';

/**
 * Hook for linking Telegram account to an existing user (requires authentication).
 *
 * Uses endpoints:
 * - POST /auth/link/telegram/start - Get bot URL and link token
 * - GET /auth/link/telegram/poll - Poll for completion status
 *
 * @example
 * const { isStarting, isPolling, error, botUrl, start, stop, reset, openTelegram } = useTelegramLink();
 *
 * // Start linking flow
 * await start(); // Opens bot URL automatically
 *
 * // Manual retry
 * openTelegram();
 *
 * // Reset state
 * reset();
 */
export function useTelegramLink() {
  const queryClient = useQueryClient();

  const isPolling = ref(false);
  const error: Ref<string | null> = ref(null);
  const botUrl: Ref<string | null> = ref(null);

  const linkToken = ref<string | null>(null);
  const pollInterval = ref<ReturnType<typeof setInterval> | null>(null);

  // Generated mutation hook for starting link flow
  const { mutateAsync: startLink, isPending: isStarting } = useStartLinkAuthLinkTelegramStartPost();

  /**
   * Stop polling and cleanup.
   */
  const stop = () => {
    if (pollInterval.value) {
      clearInterval(pollInterval.value);
      pollInterval.value = null;
    }
    isPolling.value = false;
    linkToken.value = null;
  };

  /**
   * Reset all state to initial values.
   */
  const reset = () => {
    stop();
    botUrl.value = null;
    error.value = null;
  };

  /**
   * Open bot URL in new tab (for manual retry).
   */
  const openTelegram = () => {
    if (botUrl.value) {
      window.open(botUrl.value, '_blank');
    }
  };

  /**
   * Poll the link status endpoint until completion, expiry, or timeout.
   */
  const pollStatus = async () => {
    let attempts = 0;
    const maxAttempts = 60; // 60 attempts * 3s = 3 minutes max

    const poll = async (): Promise<void> => {
      attempts++;

      if (attempts > maxAttempts) {
        stop();
        error.value = 'Login timed out.';
        return;
      }

      try {
        const response = await apiFetch(
          `/auth/link/telegram/poll?token=${linkToken.value ?? ''}`,
          { method: 'GET' }
        );

        // 410 = token expired
        if (response.status === 410) {
          stop();
          error.value = 'Login link expired.';
          return;
        }

        if (!response.ok) {
          // Non-2xx status (but not 410), continue polling
          return;
        }

        const data = (await response.json()) as TelegramLinkStatusResponse;

        if (data.status === 'completed') {
          stop();
          // Invalidate user query to refetch with linked Telegram
          await queryClient.invalidateQueries({
            queryKey: getCurrentUserUsersMeGetQueryKey(),
          });
        } else if (data.status === 'error') {
          stop();
          // Map error codes to user-friendly messages
          const errorMessages: Record<string, string> = {
            telegram_already_used: 'This Telegram account is already linked to another user.',
          };
          error.value = errorMessages[data.error ?? ''] ?? 'Linking failed.';
        }
        // status === 'pending' -> continue polling
      } catch {
        // Network error, continue polling
      }
    };

    // Start polling interval
    pollInterval.value = setInterval(() => {
      void poll();
    }, 3000); // Poll every 3 seconds
  };

  /**
   * Start the Telegram linking flow.
   * Opens bot URL and begins polling for completion.
   */
  const start = async () => {
    error.value = null;

    try {
      const response = await startLink();

      linkToken.value = response.link_token;
      botUrl.value = response.bot_url;

      // Open bot URL automatically
      window.open(response.bot_url, '_blank');

      // Start polling
      isPolling.value = true;
      await pollStatus();
    } catch {
      error.value = 'Failed to start.';
    }
  };

  // Cleanup on unmount
  onUnmounted(() => {
    stop();
  });

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
