import { useAppInit } from '@/providers/AppInitProvider';

/**
 * User roles in order of privilege (lowest to highest)
 */
export type UserRole = 'user' | 'admin' | 'owner';

/**
 * useAuth - Centralized auth state hook
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
 * if (isOwner) {
 *   // Show owner-only actions
 * } else if (isAdminOrOwner) {
 *   // Show admin pages
 * }
 */
export function useAuth() {
  const { user, isLoading, isReady, error, reinitialize } = useAppInit();

  // Backend returns GUEST user even without login
  const isGuest = !user || user.user_type === 'GUEST';
  const isAuthenticated = user?.user_type === 'REGISTERED';

  // Role checks (only valid if authenticated)
  const role = (isAuthenticated ? user.role : null) as UserRole | null;
  const isAdmin = role === 'admin';
  const isOwner = role === 'owner';
  const isAdminOrOwner = isAdmin || isOwner;

  return {
    /** Current user object (may be GUEST or REGISTERED) */
    user,
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
    isLoading,
    /** True when auth initialization is complete */
    isReady,
    /** Error during auth initialization */
    error,
    /** Reinitialize auth (call after login) */
    reinitialize,
  };
}
