'use client';

import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import {
  getCurrentUserUsersMeGetQueryKey,
  useUpdateCurrentUserUsersMePatch,
} from '@/src/gen/hooks';
import type { UserSchema } from '@/src/gen/models';

/**
 * Hook for updating current user with optimistic updates.
 *
 * Features:
 * - Optimistic UI updates (instant feedback)
 * - Automatic rollback on error
 * - Toast notifications
 * - Query cache synchronization
 *
 * @example
 * const { mutateAsync: updateUser } = useUpdateUser();
 * await updateUser({ app_language_code: 'ru' });
 */
export function useUpdateUser() {
  const queryClient = useQueryClient();

  return useUpdateCurrentUserUsersMePatch({
    mutation: {
      // Phase 1: Before server responds (optimistic update)
      onMutate: async (variables) => {
        // Cancel any outgoing queries to avoid race conditions
        await queryClient.cancelQueries({
          queryKey: getCurrentUserUsersMeGetQueryKey(),
        });

        // Snapshot the previous value for rollback
        const previousUser = queryClient.getQueryData<UserSchema>(
          getCurrentUserUsersMeGetQueryKey()
        );

        // Optimistically update the cache
        if (previousUser && variables.data) {
          queryClient.setQueryData<UserSchema>(
            getCurrentUserUsersMeGetQueryKey(),
            {
              ...previousUser,
              ...variables.data,
            }
          );
        }

        // Return context with snapshot for potential rollback
        return { previousUser };
      },

      // Phase 2: If server request fails (rollback)
      onError: (error, variables, context) => {
        // Restore the previous state
        if (context?.previousUser) {
          queryClient.setQueryData(
            getCurrentUserUsersMeGetQueryKey(),
            context.previousUser
          );
        }

        // Show error notification
        toast.error('Failed to update profile');
        console.error('Error updating user:', error);
      },

      // Phase 3: Server request succeeded (sync)
      onSuccess: () => {
        // Invalidate to ensure we're in sync with server
        void queryClient.invalidateQueries({
          queryKey: getCurrentUserUsersMeGetQueryKey(),
        });

        // Show success notification
        toast.success('Profile updated successfully');
      },
    },
  });
}
