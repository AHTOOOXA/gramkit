import { ref, onUnmounted } from 'vue';
import { useQueryClient } from '@tanstack/vue-query';
import { getCurrentUserUsersMeGetQueryKey } from '@/gen/hooks';
import { startLinkAuthLinkTelegramStartPost, pollLinkStatusAuthLinkTelegramPollGet } from '@/gen/client';

export function useTelegramWebAuth() {
  const queryClient = useQueryClient();

  const isStarting = ref(false);
  const isPolling = ref(false);
  const error = ref<string | null>(null);
  const botUrl = ref<string | null>(null);

  let pollInterval: ReturnType<typeof setInterval> | null = null;

  async function start() {
    isStarting.value = true;
    error.value = null;

    try {
      const data = await startLinkAuthLinkTelegramStartPost();
      botUrl.value = data.bot_url;

      window.open(data.bot_url, '_blank');

      isPolling.value = true;
      startPolling(data.link_token);
    } catch (err) {
      error.value = 'Failed to start. Please try again.';
      throw err;
    } finally {
      isStarting.value = false;
    }
  }

  function openTelegram() {
    if (botUrl.value) {
      window.open(botUrl.value, '_blank');
    }
  }

  function startPolling(token: string) {
    let attempts = 0;
    const maxAttempts = 60;

    pollInterval = setInterval(async () => {
      attempts++;

      if (attempts > maxAttempts) {
        stop();
        error.value = 'Login timed out. Please try again.';
        return;
      }

      try {
        const data = await pollLinkStatusAuthLinkTelegramPollGet({
          token
        });

        if (data.status === 'completed') {
          stop();
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
      } catch (err: unknown) {
        // Handle 410 status (expired)
        const axiosError = err as { response?: { status?: number } };
        if (axiosError?.response?.status === 410) {
          stop();
          error.value = 'Login link expired. Please try again.';
        }
        // Otherwise continue polling
      }
    }, 3000);
  }

  function stop() {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
    isPolling.value = false;
  }

  function reset() {
    stop();
    botUrl.value = null;
    error.value = null;
  }

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
