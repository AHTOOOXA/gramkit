import { computed, type ComputedRef } from 'vue';
import { useAppInit } from './useAppInit';
import type { UserSchema } from '@/gen/models';

/**
 * User roles in order of privilege (lowest to highest)
 */
export type UserRole = 'user' | 'admin' | 'owner';

/**
 * useAuth - Centralized auth state composable
 *
 * Provides consistent auth checks across the app.
 * Backend returns GUEST user even without login, so we check user_type.
 *
 * Roles (lowest to highest privilege):
 * - user: Regular authenticated user
 * - admin: Can access admin pages
 * - owner: Full access, can perform protected actions
 *
 * @example
 * const { isAuthenticated, isAdmin, isOwner, user } = useAuth();
 *
 * if (isOwner.value) {
 *   // Show owner-only actions
 * } else if (isAdminOrOwner.value) {
 *   // Show admin pages
 * }
 */
export function useAuth(): {
  user: ComputedRef<UserSchema | null>;
  role: ComputedRef<UserRole | null>;
  isAuthenticated: ComputedRef<boolean>;
  isGuest: ComputedRef<boolean>;
  isAdmin: ComputedRef<boolean>;
  isOwner: ComputedRef<boolean>;
  isAdminOrOwner: ComputedRef<boolean>;
  isLoading: ComputedRef<boolean>;
  isReady: ComputedRef<boolean>;
  error: ComputedRef<Error | null>;
  reinitialize: () => void;
} {
  const appInit = useAppInit();

  // Backend returns GUEST user even without login
  const isGuest = computed(() => !appInit.user.value || appInit.user.value.user_type === 'GUEST');
  const isAuthenticated = computed(() => appInit.user.value?.user_type === 'REGISTERED');

  // Role checks (only valid if authenticated)
  const role = computed(
    () => (isAuthenticated.value && appInit.user.value ? appInit.user.value.role : null) as UserRole | null
  );
  const isAdmin = computed(() => role.value === 'admin');
  const isOwner = computed(() => role.value === 'owner');
  const isAdminOrOwner = computed(() => isAdmin.value || isOwner.value);

  return {
    /** Current user object (may be GUEST or REGISTERED) */
    user: computed(() => appInit.user.value),
    /** Current role ('user' | 'admin' | 'owner' | null) */
    role,
    /** True if user is logged in (user_type === 'REGISTERED') */
    isAuthenticated,
    /** True if user is a guest (not logged in or user_type === 'GUEST') */
    isGuest,
    /** True if user has admin role */
    isAdmin,
    /** True if user has owner role (highest privilege) */
    isOwner,
    /** True if user has admin OR owner role (for admin pages) */
    isAdminOrOwner,
    /** True while auth is initializing */
    isLoading: computed(() => appInit.isLoading.value),
    /** True when auth initialization is complete */
    isReady: computed(() => appInit.isReady.value),
    /** Error during auth initialization */
    error: computed(() => appInit.error.value),
    /** Reinitialize auth (call after login) */
    reinitialize: appInit.reinitialize,
  };
}
