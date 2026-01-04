import { watch } from 'vue';
import { useRouter } from 'vue-router';
import { useAuth } from './useAuth';

/**
 * Redirect configuration.
 */
export interface AuthRedirectConfig {
  /** Route to redirect authenticated users to (default: '/') */
  redirectTo?: string;
}

const DEFAULT_CONFIG: Required<AuthRedirectConfig> = {
  redirectTo: '/',
};

/**
 * Composable to handle redirects for authenticated users.
 *
 * Automatically redirects authenticated users to the specified route.
 * Guests (unauthenticated or GUEST user_type) are not redirected.
 *
 * @example
 * ```vue
 * <script setup>
 * const { isGuest, isLoading } = useAuthRedirect();
 * </script>
 *
 * <template>
 *   <div v-if="isLoading || !isGuest">
 *     <LoadingSpinner />
 *   </div>
 *   <LoginForm v-else />
 * </template>
 * ```
 */
export function useAuthRedirect(config: AuthRedirectConfig = {}) {
  const router = useRouter();
  const { isGuest, isLoading, user } = useAuth();

  const { redirectTo } = { ...DEFAULT_CONFIG, ...config };

  // Watch for auth state changes and redirect if not a guest
  watch(
    () => isGuest.value,
    (currentIsGuest) => {
      if (!currentIsGuest) {
        void router.replace(redirectTo);
      }
    },
    { immediate: true }
  );

  return {
    /** Whether the user is a guest (not authenticated) */
    isGuest,
    /** Whether app is still loading initial auth state */
    isLoading,
    /** Current user (null if not authenticated) */
    user,
  };
}
