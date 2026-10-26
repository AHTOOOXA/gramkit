'use client';

import { useState } from 'react';
import { getErrorMessage } from '@tma-platform/core-react/errors';
import { Ellipsis, Undo2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { toast } from 'sonner';

import { formatDate } from '@/lib/admin/format';
import { useAdminList } from '@/hooks/useAdminList';
import { AdminActionDialog } from '@/components/admin/AdminActionDialog';
import { type AdminColumn } from '@/components/admin/AdminDataTable';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { type AdminUserPanelProps } from '@/config/admin/userPanels';
import { useAuth } from '@/hooks';
import { useListUserPaymentsAdminUsersUserIdPaymentsGet } from '@/src/gen/hooks/useListUserPaymentsAdminUsersUserIdPaymentsGet';
import { useRefundPaymentAdminPaymentsPaymentIdRefundPost } from '@/src/gen/hooks/useRefundPaymentAdminPaymentsPaymentIdRefundPost';
import type { AdminPaymentListItem } from '@/src/gen/models/AdminPaymentListItem';

import { AdminUserSubTable } from './AdminUserSubTable';

/**
 * AdminUserPaymentsPanel — the user's payments (paginated, sortable), with an
 * owner-only refund for successful Telegram Stars payments. A refund returns
 * the Stars and takes back the period they paid for, so it calls `onMutated`
 * and the detail page refetches the profile and the other panels.
 *
 * Registered in `coreUserPanels` (`@/config/admin/userPanels`).
 * Port of template-vue's `AdminUserPaymentsPanel.vue`.
 */
export default function AdminUserPaymentsPanel({
  userId,
  onMutated,
}: AdminUserPanelProps) {
  const t = useTranslations('admin');
  const { isAdminOrOwner, isOwner } = useAuth();

  const list = useAdminList({
    sortBy: 'created_at',
    sortDir: 'desc',
    pageSize: 10,
  });

  const payments = useListUserPaymentsAdminUsersUserIdPaymentsGet(
    userId,
    list.params,
    { query: { enabled: isAdminOrOwner && !!userId } }
  );

  // Owner-only: refund a Stars payment (the Stars go back, the period it paid for is taken back).
  const refund = useRefundPaymentAdminPaymentsPaymentIdRefundPost();
  // The row stays set after the dialog closes so the title doesn't lose its
  // amount during the exit animation; `refundOpen` drives visibility.
  const [refundRow, setRefundRow] = useState<AdminPaymentListItem | null>(null);
  const [refundOpen, setRefundOpen] = useState(false);
  const canRefund = (row: AdminPaymentListItem) =>
    row.provider_id === 'TELEGRAM_STARS' && row.status === 'SUCCEEDED';

  const confirmRefund = async () => {
    if (!refundRow) return;
    try {
      await refund.mutateAsync({ payment_id: refundRow.id });
      toast.success(t('users.payments.refundDone'));
      setRefundOpen(false);
      onMutated();
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  };

  const columns: AdminColumn<AdminPaymentListItem>[] = [
    {
      key: 'created_at',
      label: t('users.payments.date'),
      sortable: true,
      cell: (row) => (
        <span className="text-muted-foreground whitespace-nowrap">
          {formatDate(row.created_at, true)}
        </span>
      ),
    },
    {
      key: 'product_id',
      label: t('users.payments.product'),
      cell: (row) => <span className="break-all">{row.product_id}</span>,
    },
    {
      key: 'amount',
      label: t('users.payments.amount'),
      sortable: true,
      cell: (row) => (
        <span className="whitespace-nowrap tabular-nums">
          {row.amount} {row.currency}
        </span>
      ),
    },
    {
      key: 'status',
      label: t('users.payments.status'),
      sortable: true,
      cell: (row) => <Badge variant="outline">{row.status}</Badge>,
    },
    ...(isOwner
      ? [
          {
            key: 'actions',
            label: '',
            className: 'w-12 text-right',
            cell: (row: AdminPaymentListItem) =>
              canRefund(row) ? (
                <div className="flex justify-end">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        aria-label={t('users.payments.menu')}
                      >
                        <Ellipsis className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        onSelect={() => {
                          setRefundRow(row);
                          setRefundOpen(true);
                        }}
                      >
                        <Undo2 className="h-4 w-4" />
                        {t('users.payments.refund')}
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              ) : null,
          },
        ]
      : []),
  ];

  return (
    <div>
      <AdminUserSubTable
        columns={columns}
        rows={payments.data?.items ?? []}
        isLoading={payments.isLoading}
        error={payments.error}
        sortBy={list.sortBy}
        sortDir={list.sortDir}
        page={list.page}
        totalPages={payments.data?.total_pages ?? 1}
        total={payments.data?.total ?? 0}
        onSort={list.setSort}
        onRetry={() => void payments.refetch()}
        onPrev={list.prevPage}
        onNext={list.nextPage}
      />

      <AdminActionDialog
        open={refundOpen}
        onOpenChange={(open) => {
          if (!open) setRefundOpen(false);
        }}
        title={t('users.payments.refundConfirmTitle', {
          amount: refundRow?.amount ?? '',
        })}
        description={t('users.payments.refundConfirmDesc')}
        pending={refund.isPending}
        onConfirm={() => void confirmRefund()}
      />
    </div>
  );
}
