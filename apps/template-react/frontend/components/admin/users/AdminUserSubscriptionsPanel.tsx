'use client';

import { useTranslations } from 'next-intl';

import { formatDate } from '@/lib/admin/format';
import { type AdminColumn } from '@/components/admin/AdminDataTable';
import { Badge } from '@/components/ui/badge';
import { type AdminUserPanelProps } from '@/config/admin/userPanels';
import { useAuth } from '@/hooks';
import { useListUserSubscriptionsAdminUsersUserIdSubscriptionsGet } from '@/src/gen/hooks/useListUserSubscriptionsAdminUsersUserIdSubscriptionsGet';
import type { AdminUserSubscription } from '@/src/gen/models/AdminUserSubscription';

import { AdminUserSubTable } from './AdminUserSubTable';

/**
 * AdminUserSubscriptionsPanel — every subscription the user has had, newest
 * first (the endpoint returns a plain list, so there is no pager or sorting).
 *
 * Registered in `coreUserPanels` (`@/config/admin/userPanels`).
 * Port of template-vue's `AdminUserSubscriptionsPanel.vue`.
 */
export default function AdminUserSubscriptionsPanel({
  userId,
}: AdminUserPanelProps) {
  const t = useTranslations('admin');
  const { isAdminOrOwner } = useAuth();

  const subscriptions =
    useListUserSubscriptionsAdminUsersUserIdSubscriptionsGet(userId, {
      query: { enabled: isAdminOrOwner && !!userId },
    });

  const columns: AdminColumn<AdminUserSubscription>[] = [
    {
      key: 'product_id',
      label: t('users.subscriptions.product'),
      cell: (row) => (
        <span className="font-medium break-all">{row.product_id}</span>
      ),
    },
    {
      key: 'status',
      label: t('users.subscriptions.status'),
      cell: (row) => <Badge variant="outline">{row.status}</Badge>,
    },
    {
      key: 'start_date',
      label: t('users.subscriptions.start'),
      cell: (row) => (
        <span className="whitespace-nowrap">{formatDate(row.start_date)}</span>
      ),
    },
    {
      key: 'end_date',
      label: t('users.subscriptions.end'),
      cell: (row) => (
        <span className="whitespace-nowrap">{formatDate(row.end_date)}</span>
      ),
    },
  ];

  return (
    <AdminUserSubTable
      columns={columns}
      rows={subscriptions.data ?? []}
      isLoading={subscriptions.isLoading}
      error={subscriptions.error}
      hidePagination
      onRetry={() => void subscriptions.refetch()}
    />
  );
}
