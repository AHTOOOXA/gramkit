<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { toast } from 'vue-sonner';
import { ArrowLeft, Ban, Info, Pencil, Rocket } from '@lucide/vue';
import { getErrorMessage, isApiError } from '@core/errors';
import { formatDate } from '@app/admin/format';
import { useAdminLabels } from '@app/admin/useAdminLabels';
import { useAuth } from '@app/composables/useAuth';
import { useBroadcasts } from '@app/composables/useBroadcasts';
import { useGetBroadcast } from '@gen/hooks/useGetBroadcast';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import AdminActionDialog from '@app/presentation/components/admin/AdminActionDialog.vue';
import AdminStateBlock from '@app/presentation/components/admin/AdminStateBlock.vue';
import BroadcastStatsCell from '@app/presentation/components/admin/broadcasts/BroadcastStatsCell.vue';
import BroadcastStatusBadge from '@app/presentation/components/admin/broadcasts/BroadcastStatusBadge.vue';
import TelegramMessagePreview from '@app/presentation/components/admin/broadcasts/TelegramMessagePreview.vue';

/**
 * BroadcastDetail — one broadcast row: status, the stored message as a preview,
 * schedule, keyboard, and delivery counters (`GET /admin/broadcasts/{id}`
 * already carries `stats`).
 *
 * Actions: edit; cancel (active rows only — the backend reports an expired row
 * as inactive); send now to everyone (owner only), which sends this row so the
 * counters land on it. Counters update as the worker delivers; refetch to see
 * them move.
 */
const { t } = useI18n();
const { isAdminOrOwner, isOwner } = useAuth();
const { broadcastSlotLabel, broadcastTypeLabel, broadcastKeyboardLabel, broadcastKeyboardButtons } =
  useAdminLabels();
const route = useRoute();
const router = useRouter();
const { cancel, sendNow, invalidateList, invalidateOne } = useBroadcasts();

const broadcastId = computed<number | null>(() => {
  const n = Number(route.params.id);
  return Number.isInteger(n) ? n : null;
});

const { data: broadcast, isLoading, error, refetch } = useGetBroadcast(() => broadcastId.value ?? 0, {
  query: {
    enabled: () => isAdminOrOwner.value && broadcastId.value !== null,
    staleTime: 15 * 1000,
  },
});

const notFound = computed(
  () => broadcastId.value === null || (isApiError(error.value) && error.value.status === 404),
);

const isMedia = computed(() => !!broadcast.value && broadcast.value.message_type !== 'text');
const keyboardButtons = computed(() =>
  broadcast.value
    ? broadcastKeyboardButtons(broadcast.value.keyboard_type, broadcast.value.keyboard_button_text)
    : [],
);

// ── Cancel ─────────────────────────────────────────────────────────────────
const showCancel = ref(false);

const onCancelConfirm = async () => {
  const id = broadcastId.value;
  if (id === null) return;
  try {
    await cancel.mutateAsync({ broadcast_id: id });
    toast.success(t('admin.broadcasts.actions.cancelDone'));
    showCancel.value = false;
    void invalidateOne(id);
    void invalidateList();
  } catch (e) {
    toast.error(getErrorMessage(e));
  }
};

// ── Send now (owner) ───────────────────────────────────────────────────────
const showSendNow = ref(false);

const onSendNowConfirm = async () => {
  const id = broadcastId.value;
  if (id === null) return;
  try {
    await sendNow.mutateAsync({ data: { broadcast_id: id } });
    toast.success(t('admin.broadcasts.composer.sentNow'));
    showSendNow.value = false;
  } catch (e) {
    toast.error(getErrorMessage(e));
  }
};
</script>

<template>
  <div class="flex flex-col gap-4">
    <Button
      variant="ghost"
      size="sm"
      class="-ml-2 w-fit"
      @click="router.push({ name: 'admin-broadcasts' })"
    >
      <ArrowLeft class="h-4 w-4" />
      {{ t('admin.broadcasts.backToList') }}
    </Button>

    <div
      v-if="notFound"
      class="flex flex-col items-center justify-center rounded-xl border border-dashed border-border py-12 text-center text-sm text-muted-foreground"
    >
      {{ t('admin.broadcasts.detail.notFound') }}
    </div>

    <AdminStateBlock
      v-else
      :is-loading="isLoading"
      :error="error"
      @retry="refetch()"
    >
      <template #loading>
        <div class="flex flex-col gap-4">
          <Skeleton class="h-20 w-full rounded-xl" />
          <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Skeleton class="h-56 w-full rounded-xl" />
            <Skeleton class="h-56 w-full rounded-xl" />
          </div>
        </div>
      </template>

      <div
        v-if="broadcast"
        class="flex flex-col gap-4"
      >
        <!-- Header + actions -->
        <section class="flex flex-col gap-3 rounded-xl border bg-card p-4 sm:flex-row sm:items-start sm:justify-between">
          <div class="flex min-w-0 flex-col gap-1.5">
            <h2 class="text-lg font-semibold leading-tight">
              {{ t('admin.broadcasts.detail.title', { id: broadcast.id }) }}
            </h2>
            <div class="flex flex-wrap items-center gap-1.5">
              <BroadcastStatusBadge :is-active="broadcast.is_active" />
              <Badge variant="outline">{{ broadcastSlotLabel(broadcast.time_slot) }}</Badge>
              <Badge variant="outline">{{ broadcastTypeLabel(broadcast.message_type) }}</Badge>
            </div>
          </div>

          <div class="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:justify-end">
            <Button
              variant="outline"
              @click="router.push({ name: 'admin-broadcast-edit', params: { id: broadcast.id } })"
            >
              <Pencil class="h-4 w-4" />
              {{ t('admin.broadcasts.actions.edit') }}
            </Button>
            <Button
              v-if="broadcast.is_active"
              variant="outline"
              @click="showCancel = true"
            >
              <Ban class="h-4 w-4" />
              {{ t('admin.broadcasts.actions.cancel') }}
            </Button>
            <Button
              v-if="isOwner"
              variant="destructive"
              :disabled="sendNow.isPending.value"
              @click="showSendNow = true"
            >
              <Rocket class="h-4 w-4" />
              {{ t('admin.broadcasts.composer.sendNow') }}
            </Button>
          </div>
        </section>

        <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <!-- Message -->
          <section class="flex min-w-0 flex-col gap-3 rounded-xl border bg-card p-4">
            <TelegramMessagePreview
              :title="t('admin.broadcasts.detail.content')"
              :text="broadcast.message_text"
              :html="broadcast.message_html ?? broadcast.message_text"
              :text-is-html="!isMedia && broadcast.has_text_formatting"
              :media-type="isMedia ? broadcast.message_type : null"
              :caption="broadcast.has_caption_formatting ? (broadcast.caption_html ?? broadcast.caption) : broadcast.caption"
              :caption-is-html="isMedia && broadcast.has_caption_formatting"
              :keyboard-buttons="keyboardButtons"
            />
          </section>

          <div class="flex min-w-0 flex-col gap-4">
            <!-- Schedule -->
            <section class="flex flex-col gap-3 rounded-xl border bg-card p-4">
              <h3 class="text-sm font-medium">{{ t('admin.broadcasts.detail.schedule') }}</h3>
              <dl class="grid grid-cols-1 gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
                <div class="flex min-w-0 flex-col gap-0.5">
                  <dt class="text-xs text-muted-foreground">{{ t('admin.broadcasts.deadline') }}</dt>
                  <dd>{{ formatDate(broadcast.deadline, true) }}</dd>
                </div>
                <div class="flex min-w-0 flex-col gap-0.5">
                  <dt class="text-xs text-muted-foreground">{{ t('admin.broadcasts.priority') }}</dt>
                  <dd class="tabular-nums">{{ broadcast.priority }}</dd>
                </div>
                <div class="flex min-w-0 flex-col gap-0.5">
                  <dt class="text-xs text-muted-foreground">{{ t('admin.broadcasts.detail.created') }}</dt>
                  <dd>{{ formatDate(broadcast.created_at, true) }}</dd>
                </div>
                <div
                  v-if="broadcast.completed_at"
                  class="flex min-w-0 flex-col gap-0.5"
                >
                  <dt class="text-xs text-muted-foreground">{{ t('admin.broadcasts.status.completed') }}</dt>
                  <dd>{{ formatDate(broadcast.completed_at, true) }}</dd>
                </div>
              </dl>
            </section>

            <!-- Keyboard -->
            <section class="flex flex-col gap-1.5 rounded-xl border bg-card p-4">
              <h3 class="text-sm font-medium">{{ t('admin.broadcasts.detail.keyboard') }}</h3>
              <p class="text-sm">
                {{ broadcastKeyboardLabel(broadcast.keyboard_type) }}
                <span
                  v-if="keyboardButtons.length"
                  class="text-muted-foreground"
                > · {{ keyboardButtons[0] }}</span>
              </p>
            </section>

            <!-- Delivery -->
            <section class="flex flex-col gap-3 rounded-xl border bg-card p-4">
              <h3 class="text-sm font-medium">{{ t('admin.broadcasts.detail.delivery') }}</h3>
              <BroadcastStatsCell :stats="broadcast.stats" />
              <p
                v-if="broadcast.stats.last_sent_at"
                class="text-xs text-muted-foreground"
              >
                {{ t('admin.broadcasts.stats.lastSent') }}: {{ formatDate(broadcast.stats.last_sent_at, true) }}
              </p>
              <p class="flex items-start gap-1.5 text-xs text-muted-foreground">
                <Info class="mt-0.5 h-3.5 w-3.5 shrink-0" />
                {{ t('admin.broadcasts.detail.deliveryNote') }}
              </p>
            </section>
          </div>
        </div>
      </div>
    </AdminStateBlock>

    <AdminActionDialog
      :open="showCancel"
      :title="t('admin.broadcasts.actions.cancelConfirmTitle')"
      :description="t('admin.broadcasts.actions.cancelConfirmDesc')"
      :pending="cancel.isPending.value"
      @update:open="(v) => { if (!v) showCancel = false; }"
      @confirm="onCancelConfirm"
    />

    <AdminActionDialog
      :open="showSendNow"
      :title="t('admin.broadcasts.composer.sendNowConfirmTitle')"
      :description="t('admin.broadcasts.composer.sendNowConfirmDesc')"
      :pending="sendNow.isPending.value"
      :confirm-label="t('admin.broadcasts.composer.sendNow')"
      @update:open="(v) => { if (!v) showSendNow = false; }"
      @confirm="onSendNowConfirm"
    />
  </div>
</template>
