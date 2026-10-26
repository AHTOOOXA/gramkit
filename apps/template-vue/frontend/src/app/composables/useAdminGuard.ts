import { watch, type ComputedRef } from 'vue';
import { useRouter } from 'vue-router';
import { useAuth } from '@app/composables/useAuth';
import { HOME_ROUTE } from '@app/router/router';

/**
 * useAdminGuard — the SINGLE client-side guard for the admin panel.
 *
 * Call it once from the shell (AdminShell.vue); every admin section rendered
 * inside it inherits the redirect. It watches the resolved auth state and, once
 * auth has finished loading, sends non-admins back to the app home.
 *
 * This is a UX guard only — the backend RBAC (`AdminUser`/`OwnerUser`) is the
 * real authority; a non-admin who reaches an admin route just gets 403s + this
 * redirect.
 *
 * @example
 * const { isAdminOrOwner, isLoading } = useAdminGuard();
 */
export function useAdminGuard(): {
  isAdminOrOwner: ComputedRef<boolean>;
  isLoading: ComputedRef<boolean>;
} {
  const router = useRouter();
  const { isAdminOrOwner, isLoading } = useAuth();

  watch(
    [isAdminOrOwner, isLoading],
    ([allowed, loading]) => {
      // Only act once auth has resolved — never redirect while still loading,
      // or we'd bounce admins out before their role is known.
      if (!loading && !allowed) {
        router.replace(HOME_ROUTE);
      }
    },
    { immediate: true },
  );

  return { isAdminOrOwner, isLoading };
}
