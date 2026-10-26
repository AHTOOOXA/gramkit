'use client';

import { type ReactNode } from 'react';
import { ShieldAlert } from 'lucide-react';
import { useTranslations } from 'next-intl';

import { useAdminGuard } from '@/hooks/useAdminGuard';
import { Skeleton } from '@/components/ui/skeleton';

import { AdminTabs } from './AdminTabs';

/**
 * AdminShell — the frame of every /admin/* page: title, the section tabs and
 * the active page. Rendered once by `app/[locale]/(admin)/admin/layout.tsx`;
 * Next keeps the layout mounted across tab and detail navigation, so only the
 * section below the tabs swaps.
 *
 * The single client-side role guard (useAdminGuard) runs here for all
 * sections; the backend RBAC is the real authority. AppShell already pads the
 * page (and clears the mobile bottom nav), so there's no page padding here.
 *
 * Port of template-vue's `AdminShell.vue`.
 */
export function AdminShell({ children }: { children: ReactNode }) {
  const { isAdminOrOwner, isLoading } = useAdminGuard();
  const t = useTranslations('admin');

  return (
    <div className="flex flex-col gap-4 md:py-2">
      {isLoading ? (
        // While auth resolves we render a neutral skeleton; the guard
        // redirects non-admins once it knows.
        <>
          <Skeleton className="h-8 w-40" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-40 w-full" />
        </>
      ) : isAdminOrOwner ? (
        <>
          <header>
            <h1 className="text-2xl font-semibold">{t('nav.title')}</h1>
          </header>

          <AdminTabs />

          <section className="min-w-0">{children}</section>
        </>
      ) : (
        // Resolved-and-not-admin: the guard is mid-redirect; show a brief
        // notice instead of flashing section content.
        <div className="text-muted-foreground flex flex-col items-center gap-2 py-16 text-center">
          <ShieldAlert className="h-8 w-8" />
          <p>{t('state.forbidden')}</p>
        </div>
      )}
    </div>
  );
}
