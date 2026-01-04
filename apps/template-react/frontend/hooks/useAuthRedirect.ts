'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

import { useAppInit } from '@/providers/AppInitProvider';

/**
 * Check if user is a guest (not authenticated or GUEST user_type).
 */
export function isGuestUser(user: { user_type?: string } | null): boolean {
  return !user || user.user_type === 'GUEST';
}

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
 * Hook to handle redirects for authenticated users.
 *
 * Automatically redirects authenticated users to the specified route.
 * Guests (unauthenticated or GUEST user_type) are not redirected.
 *
 * @example
 * ```tsx
 * function LoginPage() {
 *   const { isGuest, isLoading } = useAuthRedirect();
 *
 *   if (isLoading || !isGuest) {
 *     return <LoadingSpinner />;
 *   }
 *
 *   return <LoginForm />;
 * }
 * ```
 */
export function useAuthRedirect(config: AuthRedirectConfig = {}) {
  const router = useRouter();
  const { user, isLoading } = useAppInit();

  const { redirectTo } = { ...DEFAULT_CONFIG, ...config };
  const isGuest = isGuestUser(user);

  useEffect(() => {
    if (!isGuest) {
      router.replace(redirectTo);
    }
  }, [isGuest, router, redirectTo]);

  return {
    /** Whether the user is a guest (not authenticated) */
    isGuest,
    /** Whether app is still loading initial auth state */
    isLoading,
    /** Current user (null if not authenticated) */
    user,
  };
}
