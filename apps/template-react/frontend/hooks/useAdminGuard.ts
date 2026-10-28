import { useEffect } from 'react';

import { useRouter } from '@/i18n/navigation';

import { useAuth } from './useAuth';

/**
 * useAdminGuard — the SINGLE client-side guard for the admin panel.
 *
 * Called once from `AdminShell` (the `/admin` layout), so every admin section
 * inherits the redirect. Once auth has finished loading, it sends non-admins
 * back to the app home.
 *
 * This is a UX guard only — the backend RBAC (`AdminUser`/`OwnerUser`) is the
 * real authority; a non-admin who reaches an admin route just gets 403s + this
 * redirect (guests included: `proxy.ts` can't see the API's session cookie).
 *
 * Port of template-vue's `useAdminGuard`.
 *
 * @example
 * const { isAdminOrOwner, isLoading } = useAdminGuard();
 */
export function useAdminGuard(): {
  isAdminOrOwner: boolean;
  isLoading: boolean;
} {
  const router = useRouter();
  const { isAdminOrOwner, isLoading } = useAuth();

  useEffect(() => {
    // Only act once auth has resolved — never redirect while still loading,
    // or we'd bounce admins out before their role is known.
    if (!isLoading && !isAdminOrOwner) {
      router.replace('/');
    }
  }, [isAdminOrOwner, isLoading, router]);

  return { isAdminOrOwner, isLoading };
}
