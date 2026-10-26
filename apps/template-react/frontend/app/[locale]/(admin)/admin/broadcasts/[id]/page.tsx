'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { getErrorMessage, isApiError } from '@tma-platform/core-react/errors';
import { ArrowLeft, Ban, Info, Pencil, Rocket } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { toast } from 'sonner';

import { formatDate } from '@/lib/admin/format';
import { useAdminLabels } from '@/hooks/useAdminLabels';
import { useBroadcasts } from '@/hooks/useBroadcasts';
import { AdminActionDialog } from '@/components/admin/AdminActionDialog';
import {
  AdminEmptyState,
  AdminStateBlock,
} from '@/components/admin/AdminStateBlock';
import { BroadcastStatsCell } from '@/components/admin/broadcasts/BroadcastStatsCell';
import { BroadcastStatusBadge } from '@/components/admin/broadcasts/BroadcastStatusBadge';
import { TelegramMessagePreview } from '@/components/admin/broadcasts/TelegramMessagePreview';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useAuth } from '@/hooks';
import { useRouter } from '@/i18n/navigation';
import { useGetBroadcast } from '@/src/gen/hooks/useGetBroadcast';

/**
 * Admin → one broadcast: status, the stored message as a preview, schedule,
 * keyboard, and delivery counters (`GET /admin/broadcasts/{id}` already
 * carries `stats`).
 *
 * Actions: edit; cancel (active rows only — the backend reports an expired row
 * as inactive); send now to everyone (owner only), which sends this row so the
 * counters land on it. Counters update as the worker delivers; refetch to see
 * them move.
 *
 * Port of template-vue's `BroadcastDetail.vue`.
 */
export default function AdminBroadcastDetailPage() {
  const t = useTranslations('admin');
  const { isAdminOrOwner, isOwner } = useAuth();
  const {
    broadcastSlotLabel,
    broadcastTypeLabel,
    broadcastKeyboardLabel,
    broadcastKeyboardButtons,
  } = useAdminLabels();
  const router = useRouter();
  const { cancel, sendNow, invalidateList, invalidateOne } = useBroadcasts();

  const params = useParams<{ id: string }>();
  const parsed = Number(params.id);
  const broadcastId = Number.isInteger(parsed) ? parsed : null;

  const {
    data: broadcast,
    isLoading,
    error,
    refetch,
  } = useGetBroadcast(broadcastId ?? 0, {
    query: {
      enabled: isAdminOrOwner && broadcastId !== null,
      staleTime: 15 * 1000,
    },
  });

  const notFound =
    broadcastId === null || (isApiError(error) && error.status === 404);

  const isMedia = !!broadcast && broadcast.message_type !== 'text';
  const keyboardButtons = broadcast
    ? broadcastKeyboardButtons(
        broadcast.keyboard_type,
        broadcast.keyboard_button_text
      )
    : [];

  // ── Cancel ───────────────────────────────────────────────────────────────
  const [showCancel, setShowCancel] = useState(false);

  const onCancelConfirm = async () => {
    if (broadcastId === null) return;
    try {
      await cancel.mutateAsync({ broadcast_id: broadcastId });
      toast.success(t('broadcasts.actions.cancelDone'));
      setShowCancel(false);
      void invalidateOne(broadcastId);
      void invalidateList();
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  };

  // ── Send now (owner) ─────────────────────────────────────────────────────
  const [showSendNow, setShowSendNow] = useState(false);

  const onSendNowConfirm = async () => {
    if (broadcastId === null) return;
    try {
      await sendNow.mutateAsync({ data: { broadcast_id: broadcastId } });
      toast.success(t('broadcasts.composer.sentNow'));
      setShowSendNow(false);
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <Button
        variant="ghost"
        size="sm"
        className="-ml-2 w-fit"
        onClick={() => {
          router.push('/admin/broadcasts');
        }}
      >
        <ArrowLeft className="h-4 w-4" />
        {t('broadcasts.backToList')}
      </Button>

      {notFound ? (
        <AdminEmptyState>{t('broadcasts.detail.notFound')}</AdminEmptyState>
      ) : (
        <AdminStateBlock
          isLoading={isLoading}
          error={error}
          onRetry={() => void refetch()}
          loading={
            <div className="flex flex-col gap-4">
              <Skeleton className="h-20 w-full rounded-xl" />
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <Skeleton className="h-56 w-full rounded-xl" />
                <Skeleton className="h-56 w-full rounded-xl" />
              </div>
            </div>
          }
        >
          {broadcast && (
            <div className="flex flex-col gap-4">
              {/* Header + actions */}
              <section className="bg-card flex flex-col gap-3 rounded-xl border p-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex min-w-0 flex-col gap-1.5">
                  <h2 className="text-lg leading-tight font-semibold">
                    {t('broadcasts.detail.title', { id: broadcast.id })}
                  </h2>
                  <div className="flex flex-wrap items-center gap-1.5">
                    <BroadcastStatusBadge isActive={broadcast.is_active} />
                    <Badge variant="outline">
                      {broadcastSlotLabel(broadcast.time_slot)}
                    </Badge>
                    <Badge variant="outline">
                      {broadcastTypeLabel(broadcast.message_type)}
                    </Badge>
                  </div>
                </div>

                <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:justify-end">
                  <Button
                    variant="outline"
                    onClick={() => {
                      router.push(
                        `/admin/broadcasts/${String(broadcast.id)}/edit`
                      );
                    }}
                  >
                    <Pencil className="h-4 w-4" />
                    {t('broadcasts.actions.edit')}
                  </Button>
                  {broadcast.is_active && (
                    <Button
                      variant="outline"
                      onClick={() => {
                        setShowCancel(true);
                      }}
                    >
                      <Ban className="h-4 w-4" />
                      {t('broadcasts.actions.cancel')}
                    </Button>
                  )}
                  {isOwner && (
                    <Button
                      variant="destructive"
                      disabled={sendNow.isPending}
                      onClick={() => {
                        setShowSendNow(true);
                      }}
                    >
                      <Rocket className="h-4 w-4" />
                      {t('broadcasts.composer.sendNow')}
                    </Button>
                  )}
                </div>
              </section>

              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                {/* Message */}
                <section className="bg-card flex min-w-0 flex-col gap-3 rounded-xl border p-4">
                  <TelegramMessagePreview
                    title={t('broadcasts.detail.content')}
                    text={broadcast.message_text}
                    html={broadcast.message_html ?? broadcast.message_text}
                    textIsHtml={!isMedia && broadcast.has_text_formatting}
                    mediaType={isMedia ? broadcast.message_type : null}
                    caption={
                      broadcast.has_caption_formatting
                        ? (broadcast.caption_html ?? broadcast.caption)
                        : broadcast.caption
                    }
                    captionIsHtml={isMedia && broadcast.has_caption_formatting}
                    keyboardButtons={keyboardButtons}
                  />
                </section>

                <div className="flex min-w-0 flex-col gap-4">
                  {/* Schedule */}
                  <section className="bg-card flex flex-col gap-3 rounded-xl border p-4">
                    <h3 className="text-sm font-medium">
                      {t('broadcasts.detail.schedule')}
                    </h3>
                    <dl className="grid grid-cols-1 gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
                      <div className="flex min-w-0 flex-col gap-0.5">
                        <dt className="text-muted-foreground text-xs">
                          {t('broadcasts.deadline')}
                        </dt>
                        <dd>{formatDate(broadcast.deadline, true)}</dd>
                      </div>
                      <div className="flex min-w-0 flex-col gap-0.5">
                        <dt className="text-muted-foreground text-xs">
                          {t('broadcasts.priority')}
                        </dt>
                        <dd className="tabular-nums">{broadcast.priority}</dd>
                      </div>
                      <div className="flex min-w-0 flex-col gap-0.5">
                        <dt className="text-muted-foreground text-xs">
                          {t('broadcasts.detail.created')}
                        </dt>
                        <dd>{formatDate(broadcast.created_at, true)}</dd>
                      </div>
                      {broadcast.completed_at && (
                        <div className="flex min-w-0 flex-col gap-0.5">
                          <dt className="text-muted-foreground text-xs">
                            {t('broadcasts.status.completed')}
                          </dt>
                          <dd>{formatDate(broadcast.completed_at, true)}</dd>
                        </div>
                      )}
                    </dl>
                  </section>

                  {/* Keyboard */}
                  <section className="bg-card flex flex-col gap-1.5 rounded-xl border p-4">
                    <h3 className="text-sm font-medium">
                      {t('broadcasts.detail.keyboard')}
                    </h3>
                    <p className="text-sm">
                      {broadcastKeyboardLabel(broadcast.keyboard_type)}
                      {keyboardButtons.length > 0 && (
                        <span className="text-muted-foreground">
                          {' '}
                          · {keyboardButtons[0]}
                        </span>
                      )}
                    </p>
                  </section>

                  {/* Delivery */}
                  <section className="bg-card flex flex-col gap-3 rounded-xl border p-4">
                    <h3 className="text-sm font-medium">
                      {t('broadcasts.detail.delivery')}
                    </h3>
                    <BroadcastStatsCell stats={broadcast.stats} />
                    {broadcast.stats.last_sent_at && (
                      <p className="text-muted-foreground text-xs">
                        {t('broadcasts.stats.lastSent')}:{' '}
                        {formatDate(broadcast.stats.last_sent_at, true)}
                      </p>
                    )}
                    <p className="text-muted-foreground flex items-start gap-1.5 text-xs">
                      <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                      {t('broadcasts.detail.deliveryNote')}
                    </p>
                  </section>
                </div>
              </div>
            </div>
          )}
        </AdminStateBlock>
      )}

      <AdminActionDialog
        open={showCancel}
        onOpenChange={setShowCancel}
        title={t('broadcasts.actions.cancelConfirmTitle')}
        description={t('broadcasts.actions.cancelConfirmDesc')}
        pending={cancel.isPending}
        onConfirm={() => void onCancelConfirm()}
      />

      <AdminActionDialog
        open={showSendNow}
        onOpenChange={setShowSendNow}
        title={t('broadcasts.composer.sendNowConfirmTitle')}
        description={t('broadcasts.composer.sendNowConfirmDesc')}
        pending={sendNow.isPending}
        confirmLabel={t('broadcasts.composer.sendNow')}
        onConfirm={() => void onSendNowConfirm()}
      />
    </div>
  );
}
