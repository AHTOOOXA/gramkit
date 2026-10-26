<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { toast } from 'vue-sonner';
import { AlertTriangle, Ban, Pencil, Plus } from '@lucide/vue';
import { getErrorMessage } from '@core/errors';
import { formatDate } from '@app/admin/format';
import { useAdminLabels } from '@app/admin/useAdminLabels';
import { useAuth } from '@app/composables/useAuth';
import { useBroadcasts } from '@app/composables/useBroadcasts';
import { useListBroadcasts } from '@gen/hooks/useListBroadcasts';
import type { BroadcastListItem } from '@gen/models/BroadcastListItem';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import AdminStateBlock from '@app/presentation/components/admin/AdminStateBlock.vue';
import AdminActionDialog from '@app/presentation/components/admin/AdminActionDialog.vue';
import BroadcastStatusBadge from '@app/presentation/components/admin/broadcasts/BroadcastStatusBadge.vue';
import BroadcastStatsCell from '@app/presentation/components/admin/broadcasts/BroadcastStatsCell.vue';

/**
 * BroadcastsList — active (scheduled) and completed broadcasts from the core
 * admin API, with status, delivery counters and edit / cancel. A row opens the
 * detail page. Expired rows come back inactive, so they list under Completed.
 *
 * Warns when more than one active broadcast shares a time slot: only the
 * highest-priority one is sent per cycle.
 */
const { t } = useI18n();
const { isAdminOrOwner } = useAuth();
const { broadcastSlotLabel, broadcastTypeLabel } = useAdminLabels();
const router = useRouter();
const { cancel, invalidateList, invalidateOne } = useBroadcasts();

const { data, isLoading, error, refetch } = useListBroadcasts({
  query: { enabled: () => isAdminOrOwner.value, staleTime: 15 * 1000 },
});

const active = computed<BroadcastListItem[]>(() => data.value?.active ?? []);
const completed = computed<BroadcastListItem[]>(() => data.value?.completed ?? []);
const isEmpty = computed(() => active.value.length === 0 && completed.value.length === 0);

/** Slots with more than one active broadcast (only the top-priority one sends per cycle). */
const overloadedSlots = computed<string[]>(() =>
  Object.entries(data.value?.active_by_time_slot ?? {})
    .filter(([, count]) => count > 1)
    .map(([slot]) => slot),
);

const statsOf = (b: BroadcastListItem) => ({
  sent_count: b.sent_count,
  success_count: b.success_count,
  fail_count: b.fail_count,
  cycles_run: b.cycles_run,
  last_sent_at: b.last_sent_at,
});

const cancelTarget = ref<BroadcastListItem | null>(null);

const onCancelConfirm = async () => {
  const target = cancelTarget.value;
  if (!target) return;
  try {
    await cancel.mutateAsync({ broadcast_id: target.id });
    toast.success(t('admin.broadcasts.actions.cancelDone'));
    cancelTarget.value = null;
    void invalidateList();
    void invalidateOne(target.id);
  } catch (e) {
    // Keep the dialog open so the admin can retry.
    toast.error(getErrorMessage(e));
  }
};
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <p class="text-sm text-muted-foreground">{{ t('admin.broadcasts.description') }}</p>
      <Button
        class="w-fit shrink-0"
        @click="router.push({ name: 'admin-broadcast-new' })"
      >
        <Plus class="h-4 w-4" />
        {{ t('admin.broadcasts.new') }}
      </Button>
    </div>

    <div
      v-if="overloadedSlots.length"
      class="flex items-start gap-2 rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-300"
    >
      <AlertTriangle class="mt-0.5 h-4 w-4 shrink-0" />
      <span>
        {{ t('admin.broadcasts.slotWarning', { slots: overloadedSlots.map(broadcastSlotLabel).join(', ') }) }}
      </span>
    </div>

    <AdminStateBlock
      :is-loading="isLoading"
      :error="error"
      :is-empty="isEmpty"
      @retry="refetch()"
    >
      <template #loading>
        <div class="flex flex-col gap-2">
          <Skeleton
            v-for="i in 3"
            :key="i"
            class="h-24 w-full rounded-xl"
          />
        </div>
      </template>

      <div class="flex flex-col gap-6">
        <!-- Active -->
        <section
          v-if="active.length"
          class="flex flex-col gap-2"
        >
          <h2 class="text-sm font-medium">{{ t('admin.broadcasts.activeTitle') }}</h2>
          <div
            v-for="b in active"
            :key="b.id"
            class="flex flex-col gap-3 rounded-xl border bg-card p-4 transition-colors hover:bg-accent/40 sm:flex-row sm:items-center"
          >
            <RouterLink
              :to="{ name: 'admin-broadcast-detail', params: { id: b.id } }"
              class="flex min-w-0 flex-1 flex-col gap-1.5 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <div class="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                <BroadcastStatusBadge :is-active="b.is_active" />
                <span>{{ broadcastSlotLabel(b.time_slot) }}</span>
                <span>· {{ broadcastTypeLabel(b.message_type) }}</span>
                <span>· {{ t('admin.broadcasts.priority') }} {{ b.priority }}</span>
              </div>
              <span class="line-clamp-2 break-words text-sm">{{ b.preview }}</span>
              <span class="text-xs text-muted-foreground">
                {{ t('admin.broadcasts.deadline') }}: {{ formatDate(b.deadline, true) }}
              </span>
            </RouterLink>

            <BroadcastStatsCell
              class="sm:w-40 sm:shrink-0"
              :stats="statsOf(b)"
            />

            <div class="flex shrink-0 items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                @click="router.push({ name: 'admin-broadcast-edit', params: { id: b.id } })"
              >
                <Pencil class="h-4 w-4" />
                {{ t('admin.broadcasts.actions.edit') }}
              </Button>
              <Button
                size="sm"
                variant="outline"
                @click="cancelTarget = b"
              >
                <Ban class="h-4 w-4" />
                {{ t('admin.broadcasts.actions.cancel') }}
              </Button>
            </div>
          </div>
        </section>

        <!-- Completed (cancelled, expired or finished) -->
        <section
          v-if="completed.length"
          class="flex flex-col gap-2"
        >
          <h2 class="text-sm font-medium">{{ t('admin.broadcasts.completedTitle') }}</h2>
          <RouterLink
            v-for="b in completed"
            :key="b.id"
            :to="{ name: 'admin-broadcast-detail', params: { id: b.id } }"
            class="flex flex-col gap-3 rounded-xl border bg-card/60 p-4 transition-colors hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:flex-row sm:items-center"
          >
            <div class="flex min-w-0 flex-1 flex-col gap-1.5">
              <div class="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                <BroadcastStatusBadge :is-active="b.is_active" />
                <span>{{ broadcastSlotLabel(b.time_slot) }}</span>
                <span>· {{ broadcastTypeLabel(b.message_type) }}</span>
              </div>
              <span class="line-clamp-2 break-words text-sm text-muted-foreground">{{ b.preview }}</span>
            </div>
            <BroadcastStatsCell
              class="sm:w-40 sm:shrink-0"
              :stats="statsOf(b)"
            />
          </RouterLink>
        </section>
      </div>
    </AdminStateBlock>

    <AdminActionDialog
      :open="cancelTarget !== null"
      :title="t('admin.broadcasts.actions.cancelConfirmTitle')"
      :description="t('admin.broadcasts.actions.cancelConfirmDesc')"
      :pending="cancel.isPending.value"
      @update:open="(v) => { if (!v) cancelTarget = null; }"
      @confirm="onCancelConfirm"
    />
  </div>
</template>
