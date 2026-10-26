<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { toast } from 'vue-sonner';
import { Ellipsis, Undo2 } from '@lucide/vue';
import { getErrorMessage } from '@core/errors';
import { useAdminList } from '@core/composables';
import { useAuth } from '@app/composables/useAuth';
import { formatDate } from '@app/admin/format';
import { useListUserPaymentsAdminUsersUserIdPaymentsGet } from '@gen/hooks/useListUserPaymentsAdminUsersUserIdPaymentsGet';
import { useRefundPaymentAdminPaymentsPaymentIdRefundPost } from '@gen/hooks/useRefundPaymentAdminPaymentsPaymentIdRefundPost';
import type { AdminPaymentListItem } from '@gen/models/AdminPaymentListItem';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { AdminColumn } from '@app/presentation/components/admin/AdminDataTable.vue';
import AdminActionDialog from '@app/presentation/components/admin/AdminActionDialog.vue';
import AdminUserSubTable from './AdminUserSubTable.vue';

/**
 * AdminUserPaymentsPanel — the user's payments (paginated, sortable), with an
 * owner-only refund for successful Telegram Stars payments. A refund returns
 * the Stars and takes back the period they paid for, so it emits `mutated` and
 * the detail page refetches the profile and the other panels.
 *
 * Registered in `coreUserPanels` (`@app/admin/userPanels`).
 */
const props = defineProps<{ userId: string }>();
const emit = defineEmits<{ mutated: [] }>();

const { t } = useI18n();
const { isAdminOrOwner, isOwner } = useAuth();

const list = useAdminList({ sortBy: 'created_at', sortDir: 'desc', pageSize: 10 });

const payments = useListUserPaymentsAdminUsersUserIdPaymentsGet(() => props.userId, list.params, {
  query: { enabled: () => isAdminOrOwner.value && !!props.userId },
});

const rows = computed<AdminPaymentListItem[]>(() => payments.data.value?.items ?? []);

const columns = computed<AdminColumn[]>(() => [
  { key: 'created_at', label: t('admin.users.payments.date'), sortable: true },
  { key: 'product_id', label: t('admin.users.payments.product') },
  { key: 'amount', label: t('admin.users.payments.amount'), sortable: true },
  { key: 'status', label: t('admin.users.payments.status'), sortable: true },
  ...(isOwner.value ? [{ key: 'actions', label: '', class: 'w-12 text-right' }] : []),
]);

// Owner-only: refund a Stars payment (the Stars go back, the period it paid for is taken back).
const refund = useRefundPaymentAdminPaymentsPaymentIdRefundPost();
// The row stays set after the dialog closes so the title doesn't lose its
// amount during the exit animation; `refundOpen` drives visibility.
const refundRow = ref<AdminPaymentListItem | null>(null);
const refundOpen = ref(false);
const openRefund = (row: AdminPaymentListItem) => {
  refundRow.value = row;
  refundOpen.value = true;
};
const canRefund = (row: AdminPaymentListItem) =>
  row.provider_id === 'TELEGRAM_STARS' && row.status === 'SUCCEEDED';

const confirmRefund = async () => {
  if (!refundRow.value) return;
  try {
    await refund.mutateAsync({ payment_id: refundRow.value.id });
    toast.success(t('admin.users.payments.refundDone'));
    refundOpen.value = false;
    emit('mutated');
  } catch (e) {
    toast.error(getErrorMessage(e));
  }
};
</script>

<template>
  <div>
    <AdminUserSubTable
      :columns="columns"
      :rows="rows"
      :is-loading="payments.isLoading.value"
      :error="payments.error.value"
      :sort-by="list.sortBy.value"
      :sort-dir="list.sortDir.value"
      :page="list.page.value"
      :total-pages="payments.data.value?.total_pages ?? 1"
      :total="payments.data.value?.total ?? 0"
      @sort="list.setSort"
      @retry="payments.refetch()"
      @prev="list.prevPage"
      @next="list.nextPage"
    >
      <template #cell-created_at="{ row }">
        <span class="whitespace-nowrap text-muted-foreground">{{ formatDate(row.created_at, true) }}</span>
      </template>
      <template #cell-product_id="{ row }">
        <span class="break-all">{{ row.product_id }}</span>
      </template>
      <template #cell-amount="{ row }">
        <span class="whitespace-nowrap tabular-nums">{{ row.amount }} {{ row.currency }}</span>
      </template>
      <template #cell-status="{ row }">
        <Badge variant="outline">{{ row.status }}</Badge>
      </template>
      <template #cell-actions="{ row }">
        <div
          v-if="canRefund(row)"
          class="flex justify-end"
        >
          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <Button
                size="icon-sm"
                variant="ghost"
                :aria-label="t('admin.users.payments.menu')"
              >
                <Ellipsis class="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem @select="openRefund(row)">
                <Undo2 class="h-4 w-4" />
                {{ t('admin.users.payments.refund') }}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </template>
    </AdminUserSubTable>

    <AdminActionDialog
      :open="refundOpen"
      :title="t('admin.users.payments.refundConfirmTitle', { amount: refundRow?.amount ?? '' })"
      :description="t('admin.users.payments.refundConfirmDesc')"
      :pending="refund.isPending.value"
      @update:open="(v: boolean) => { if (!v) refundOpen = false; }"
      @confirm="confirmRefund"
    />
  </div>
</template>
