'use client';

import { useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';

import { useLogoutAuthLogoutPost } from '@/src/gen/hooks';
import { useAppInit } from '@/providers/AppInitProvider';

/**
 * Logout hook with automatic cache clearing and redirect.
 *
 * Features:
 * - Clears all query cache on logout
 * - Triggers reinitialize to update AppInitProvider state
 * - Redirects to home page
 * - Error handling
 */
export function useLogout() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const { reinitialize } = useAppInit();

  return useLogoutAuthLogoutPost({
    mutation: {
      onSuccess: () => {
        // Clear all cached data
        queryClient.clear();

        // Reinitialize app state (will fail auth and set user to null)
        reinitialize();

        // Redirect to home
        if (typeof window !== 'undefined') {
          router.push('/');
        }
      },
      onError: (error) => {
        console.error('Logout failed:', error);
        // Don't show toast - logout should always succeed
        // Just clear cache and redirect anyway
        queryClient.clear();
        reinitialize();
        if (typeof window !== 'undefined') {
          router.push('/');
        }
      },
    },
  });
}
