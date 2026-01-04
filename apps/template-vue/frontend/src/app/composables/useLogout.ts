import { computed, type ComputedRef } from 'vue';
import { useRouter } from 'vue-router';
import { useQueryClient } from '@tanstack/vue-query';
import { useLogoutAuthLogoutPost } from '@gen/hooks/useLogoutAuthLogoutPost';
import { useAppInit } from './useAppInit';

/**
 * Logout composable with automatic cache clearing and redirect.
 *
 * Features:
 * - Clears all query cache on logout
 * - Triggers reinitialize to update AppInit state
 * - Redirects to home page
 * - Error handling
 */
export function useLogout(): {
  mutate: () => void;
  mutateAsync: () => Promise<void>;
  isPending: ComputedRef<boolean>;
} {
  const queryClient = useQueryClient();
  const router = useRouter();
  const { reinitialize } = useAppInit();

  const logoutMutation = useLogoutAuthLogoutPost({
    mutation: {
      onSuccess: () => {
        // Clear all cached data
        queryClient.clear();

        // Reinitialize app state (will fail auth and set user to null)
        reinitialize();

        // Redirect to home
        void router.push('/');
      },
      onError: (error) => {
        console.error('Logout failed:', error);
        // Don't show toast - logout should always succeed
        // Just clear cache and redirect anyway
        queryClient.clear();
        reinitialize();
        void router.push('/');
      },
    },
  });

  return {
    mutate: () => logoutMutation.mutate(),
    mutateAsync: async () => {
      await logoutMutation.mutateAsync();
    },
    isPending: computed(() => logoutMutation.isPending.value),
  };
}
