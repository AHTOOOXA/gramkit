<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAuth } from '@app/composables/useAuth';
import { formatDate } from '@app/admin/format';
import { useListUserSubscriptionsAdminUsersUserIdSubscriptionsGet } from '@gen/hooks/useListUserSubscriptionsAdminUsersUserIdSubscriptionsGet';
import type { AdminUserSubscription } from '@gen/models/AdminUserSubscription';
import { Badge } from '@/components/ui/badge';
import type { AdminColumn } from '@app/presentation/components/admin/AdminDataTable.vue';
import AdminUserSubTable from './AdminUserSubTable.vue';

/**
 * AdminUserSubscriptionsPanel — every subscription the user has had, newest
 * first (the endpoint returns a plain list, so there is no pager or sorting).
 *
 * Registered in `coreUserPanels` (`@app/admin/userPanels`).
 */
const props = defineProps<{ userId: string }>();

const { t } = useI18n();
const { isAdminOrOwner } = useAuth();

const subscriptions = useListUserSubscriptionsAdminUsersUserIdSubscriptionsGet(() => props.userId, {
  query: { enabled: () => isAdminOrOwner.value && !!props.userId },
});

const rows = computed<AdminUserSubscription[]>(() => subscriptions.data.value ?? []);

const columns = computed<AdminColumn[]>(() => [
  { key: 'product_id', label: t('admin.users.subscriptions.product') },
  { key: 'status', label: t('admin.users.subscriptions.status') },
  { key: 'start_date', label: t('admin.users.subscriptions.start') },
  { key: 'end_date', label: t('admin.users.subscriptions.end') },
]);
</script>

<template>
  <AdminUserSubTable
    :columns="columns"
    :rows="rows"
    :is-loading="subscriptions.isLoading.value"
    :error="subscriptions.error.value"
    hide-pagination
    @retry="subscriptions.refetch()"
  >
    <template #cell-product_id="{ row }">
      <span class="break-all font-medium">{{ row.product_id }}</span>
    </template>
    <template #cell-status="{ row }">
      <Badge variant="outline">{{ row.status }}</Badge>
    </template>
    <template #cell-start_date="{ row }">
      <span class="whitespace-nowrap">{{ formatDate(row.start_date) }}</span>
    </template>
    <template #cell-end_date="{ row }">
      <span class="whitespace-nowrap">{{ formatDate(row.end_date) }}</span>
    </template>
  </AdminUserSubTable>
</template>
