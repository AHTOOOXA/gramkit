'use client';

import { useState } from 'react';
import { getErrorMessage } from '@tma-platform/core-react/errors';
import { AlertTriangle, Ban, Pencil, Plus } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { toast } from 'sonner';

import { formatDate } from '@/lib/admin/format';
import { useAdminLabels } from '@/hooks/useAdminLabels';
import { useBroadcasts } from '@/hooks/useBroadcasts';
import { AdminActionDialog } from '@/components/admin/AdminActionDialog';
import { AdminStateBlock } from '@/components/admin/AdminStateBlock';
import { BroadcastStatsCell } from '@/components/admin/broadcasts/BroadcastStatsCell';
import { BroadcastStatusBadge } from '@/components/admin/broadcasts/BroadcastStatusBadge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useAuth } from '@/hooks';
import { Link, useRouter } from '@/i18n/navigation';
import { useListBroadcasts } from '@/src/gen/hooks/useListBroadcasts';
import type { BroadcastListItem } from '@/src/gen/models/BroadcastListItem';

const statsOf = (b: BroadcastListItem) => ({
  sent_count: b.sent_count,
  success_count: b.success_count,
  fail_count: b.fail_count,
  cycles_run: b.cycles_run,
  last_sent_at: b.last_sent_at,
});

/**
 * Admin → Broadcasts — active (scheduled) and completed broadcasts from the
 * core admin API, with status, delivery counters and edit / cancel. A row
 * opens the detail page. Expired rows come back inactive, so they list under
 * Completed.
 *
 * Warns when more than one active broadcast shares a time slot: only the
 * highest-priority one is sent per cycle.
 *
 * Port of template-vue's `BroadcastsList.vue`.
 */
export default function AdminBroadcastsPage() {
  const t = useTranslations('admin');
  const { isAdminOrOwner } = useAuth();
  const { broadcastSlotLabel, broadcastTypeLabel } = useAdminLabels();
  const router = useRouter();
  const { cancel, invalidateList, invalidateOne } = useBroadcasts();

  const { data, isLoading, error, refetch } = useListBroadcasts({
    query: { enabled: isAdminOrOwner, staleTime: 15 * 1000 },
  });

  const active = data?.active ?? [];
  const completed = data?.completed ?? [];
  const isEmpty = active.length === 0 && completed.length === 0;

  /** Slots with more than one active broadcast (only the top-priority one sends per cycle). */
  const overloadedSlots = Object.entries(data?.active_by_time_slot ?? {})
    .filter(([, count]) => count > 1)
    .map(([slot]) => slot);

  const [cancelTarget, setCancelTarget] = useState<BroadcastListItem | null>(
    null
  );

  const onCancelConfirm = async () => {
    const target = cancelTarget;
    if (!target) return;
    try {
      await cancel.mutateAsync({ broadcast_id: target.id });
      toast.success(t('broadcasts.actions.cancelDone'));
      setCancelTarget(null);
      void invalidateList();
      void invalidateOne(target.id);
    } catch (e) {
      // Keep the dialog open so the admin can retry.
      toast.error(getErrorMessage(e));
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-muted-foreground text-sm">
          {t('broadcasts.description')}
        </p>
        <Button
          className="w-fit shrink-0"
          onClick={() => {
            router.push('/admin/broadcasts/new');
          }}
        >
          <Plus className="h-4 w-4" />
          {t('broadcasts.new')}
        </Button>
      </div>

      {overloadedSlots.length > 0 && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-300">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            {t('broadcasts.slotWarning', {
              slots: overloadedSlots.map(broadcastSlotLabel).join(', '),
            })}
          </span>
        </div>
      )}

      <AdminStateBlock
        isLoading={isLoading}
        error={error}
        isEmpty={isEmpty}
        onRetry={() => void refetch()}
        loading={
          <div className="flex flex-col gap-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-24 w-full rounded-xl" />
            ))}
          </div>
        }
      >
        <div className="flex flex-col gap-6">
          {/* Active */}
          {active.length > 0 && (
            <section className="flex flex-col gap-2">
              <h2 className="text-sm font-medium">
                {t('broadcasts.activeTitle')}
              </h2>
              {active.map((b) => (
                <div
                  key={b.id}
                  className="bg-card hover:bg-accent/40 flex flex-col gap-3 rounded-xl border p-4 transition-colors sm:flex-row sm:items-center"
                >
                  <Link
                    href={`/admin/broadcasts/${String(b.id)}`}
                    className="focus-visible:ring-ring flex min-w-0 flex-1 flex-col gap-1.5 rounded-md focus-visible:ring-2 focus-visible:outline-none"
                  >
                    <div className="text-muted-foreground flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
                      <BroadcastStatusBadge isActive={b.is_active} />
                      <span>{broadcastSlotLabel(b.time_slot)}</span>
                      <span>· {broadcastTypeLabel(b.message_type)}</span>
                      <span>
                        · {t('broadcasts.priority')} {b.priority}
                      </span>
                    </div>
                    <span className="line-clamp-2 text-sm break-words">
                      {b.preview}
                    </span>
                    <span className="text-muted-foreground text-xs">
                      {t('broadcasts.deadline')}: {formatDate(b.deadline, true)}
                    </span>
                  </Link>

                  <BroadcastStatsCell
                    className="sm:w-40 sm:shrink-0"
                    stats={statsOf(b)}
                  />

                  <div className="flex shrink-0 items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        router.push(`/admin/broadcasts/${String(b.id)}/edit`);
                      }}
                    >
                      <Pencil className="h-4 w-4" />
                      {t('broadcasts.actions.edit')}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setCancelTarget(b);
                      }}
                    >
                      <Ban className="h-4 w-4" />
                      {t('broadcasts.actions.cancel')}
                    </Button>
                  </div>
                </div>
              ))}
            </section>
          )}

          {/* Completed (cancelled, expired or finished) */}
          {completed.length > 0 && (
            <section className="flex flex-col gap-2">
              <h2 className="text-sm font-medium">
                {t('broadcasts.completedTitle')}
              </h2>
              {completed.map((b) => (
                <Link
                  key={b.id}
                  href={`/admin/broadcasts/${String(b.id)}`}
                  className="bg-card/60 hover:bg-accent/40 focus-visible:ring-ring flex flex-col gap-3 rounded-xl border p-4 transition-colors focus-visible:ring-2 focus-visible:outline-none sm:flex-row sm:items-center"
                >
                  <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                    <div className="text-muted-foreground flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
                      <BroadcastStatusBadge isActive={b.is_active} />
                      <span>{broadcastSlotLabel(b.time_slot)}</span>
                      <span>· {broadcastTypeLabel(b.message_type)}</span>
                    </div>
                    <span className="text-muted-foreground line-clamp-2 text-sm break-words">
                      {b.preview}
                    </span>
                  </div>
                  <BroadcastStatsCell
                    className="sm:w-40 sm:shrink-0"
                    stats={statsOf(b)}
                  />
                </Link>
              ))}
            </section>
          )}
        </div>
      </AdminStateBlock>

      <AdminActionDialog
        open={cancelTarget !== null}
        onOpenChange={(open) => {
          if (!open) setCancelTarget(null);
        }}
        title={t('broadcasts.actions.cancelConfirmTitle')}
        description={t('broadcasts.actions.cancelConfirmDesc')}
        pending={cancel.isPending}
        onConfirm={() => void onCancelConfirm()}
      />
    </div>
  );
}
