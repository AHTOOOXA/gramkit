'use client';

import { lazy, Suspense } from 'react';
import { useParams } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { useTranslations } from 'next-intl';

import { formatDate, roleVariant, userLabel } from '@/lib/admin/format';
import { useAdminLabels } from '@/hooks/useAdminLabels';
import { AdminStateBlock } from '@/components/admin/AdminStateBlock';
import { AdminUserActions } from '@/components/admin/users/AdminUserActions';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { adminUserPanels } from '@/config/admin/userPanels';
import { useAuth } from '@/hooks';
import { useRouter } from '@/i18n/navigation';
import { useGetUserDetailAdminUsersUserIdGet } from '@/src/gen/hooks/useGetUserDetailAdminUsersUserIdGet';

// Built once at module scope (the React twin of Vue's
// `markRaw(defineAsyncComponent(...))`), so a panel never remounts on render.
const panels = adminUserPanels.map((panel) => ({
  key: panel.key,
  labelKey: panel.labelKey,
  Component: lazy(panel.loader),
}));

/** Kubb query keys look like [{ url: '/admin/users/:user_id/payments', params }, query]. */
const keyUrl = (queryKey: readonly unknown[]): string => {
  const head = queryKey[0] as { url?: unknown } | undefined;
  return typeof head?.url === 'string' ? head.url : '';
};

/**
 * Admin → user detail — profile card, the actions panel, and a tab per entry
 * in `adminUserPanels` (payments and subscriptions from core, plus any the app
 * registers in `@/config/admin/app-userPanels.ts`). Each panel gets `userId`
 * and owns its own query.
 *
 * After any mutation (an action here, or a panel's `onMutated`) it refetches
 * the profile and invalidates every `/admin/users/:user_id/...` query, which
 * covers the core panels and app panels alike.
 *
 * Port of template-vue's `AdminUserDetail.vue`.
 */
export default function AdminUserDetailPage() {
  const t = useTranslations();
  const { isAdminOrOwner } = useAuth();
  const { roleLabel, userTypeLabel } = useAdminLabels();
  const router = useRouter();
  const queryClient = useQueryClient();

  const params = useParams<{ id: string }>();
  const userId = params.id;

  const {
    data: user,
    isLoading,
    error,
    refetch,
  } = useGetUserDetailAdminUsersUserIdGet(userId, {
    // Passing `enabled` replaces Kubb's own `!!user_id` check, so repeat it.
    query: { enabled: isAdminOrOwner && !!userId, staleTime: 15 * 1000 },
  });

  const onMutated = () => {
    void refetch();
    // The one url-prefix predicate in the app (frontend-api.md prefers the
    // generated `…QueryKey()` helpers): app-registered panels own queries whose
    // keys this page can't know, so match every `/admin/users/:user_id/...` key.
    void queryClient.invalidateQueries({
      predicate: (q) => keyUrl(q.queryKey).startsWith('/admin/users/:user_id/'),
    });
  };

  const onReset = () => {
    // The user no longer exists; drop cached lists and go back to them.
    void queryClient.invalidateQueries({
      predicate: (q) => keyUrl(q.queryKey).startsWith('/admin/users'),
    });
    router.push('/admin/users');
  };

  const initials = user ? userLabel(user).charAt(0).toUpperCase() : '?';

  return (
    <div className="flex flex-col gap-4">
      <Button
        variant="ghost"
        size="sm"
        className="-ml-2 w-fit"
        onClick={() => {
          router.push('/admin/users');
        }}
      >
        <ArrowLeft className="h-4 w-4" />
        {t('admin.users.backToList')}
      </Button>

      <AdminStateBlock
        isLoading={isLoading}
        error={error}
        onRetry={() => void refetch()}
        loading={
          <div className="flex flex-col gap-4">
            <Skeleton className="h-32 w-full rounded-xl" />
            <Skeleton className="h-28 w-full rounded-xl" />
            <Skeleton className="h-48 w-full rounded-xl" />
          </div>
        }
      >
        {user && (
          <div className="flex flex-col gap-4">
            {/* Profile */}
            <section className="bg-card flex flex-col gap-4 rounded-xl border p-4">
              <div className="flex items-start gap-3">
                <Avatar className="size-12 shrink-0">
                  {user.avatar_url && (
                    <AvatarImage src={user.avatar_url} alt={userLabel(user)} />
                  )}
                  <AvatarFallback>{initials}</AvatarFallback>
                </Avatar>
                <div className="flex min-w-0 flex-col gap-1.5">
                  <h2 className="text-lg leading-tight font-semibold break-words">
                    {userLabel(user)}
                  </h2>
                  <div className="flex flex-wrap items-center gap-1.5">
                    <Badge variant={roleVariant(user.role)}>
                      {roleLabel(user.role)}
                    </Badge>
                    <Badge variant="outline">
                      {userTypeLabel(user.user_type)}
                    </Badge>
                    {user.has_active_subscription && (
                      <Badge variant="default">
                        {t('admin.users.profile.subActive')}
                      </Badge>
                    )}
                  </div>
                </div>
              </div>

              <dl className="grid grid-cols-1 gap-x-6 gap-y-3 text-sm sm:grid-cols-3">
                <div className="flex min-w-0 flex-col gap-0.5">
                  <dt className="text-muted-foreground text-xs">
                    {t('admin.users.profile.telegram')}
                  </dt>
                  <dd className="break-words">
                    <span className="tabular-nums">
                      {user.telegram_id ?? '—'}
                    </span>
                    {user.tg_username && (
                      <span className="text-muted-foreground">
                        {' '}
                        · @{user.tg_username}
                      </span>
                    )}
                  </dd>
                </div>
                <div className="flex min-w-0 flex-col gap-0.5">
                  <dt className="text-muted-foreground text-xs">
                    {t('admin.users.profile.email')}
                  </dt>
                  <dd className="break-all">{user.email ?? '—'}</dd>
                </div>
                <div className="flex min-w-0 flex-col gap-0.5">
                  <dt className="text-muted-foreground text-xs">
                    {t('admin.users.profile.joined')}
                  </dt>
                  <dd>{formatDate(user.created_at, true)}</dd>
                </div>
              </dl>
            </section>

            {/* Actions */}
            <AdminUserActions
              user={user}
              onMutated={onMutated}
              onReset={onReset}
            />

            {/* Panels */}
            {panels.length > 0 && (
              <Tabs defaultValue={panels[0]?.key} className="w-full gap-3">
                <TabsList className="max-w-full justify-start overflow-x-auto">
                  {panels.map((panel) => (
                    <TabsTrigger
                      key={panel.key}
                      value={panel.key}
                      className="flex-none"
                    >
                      {t(panel.labelKey)}
                    </TabsTrigger>
                  ))}
                </TabsList>

                {panels.map(({ key, Component }) => (
                  <TabsContent key={key} value={key}>
                    <Suspense fallback={<Skeleton className="h-40 w-full" />}>
                      <Component userId={userId} onMutated={onMutated} />
                    </Suspense>
                  </TabsContent>
                ))}
              </Tabs>
            )}
          </div>
        )}
      </AdminStateBlock>
    </div>
  );
}
