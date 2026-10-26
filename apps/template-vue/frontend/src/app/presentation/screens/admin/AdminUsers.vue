<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useAuth } from '@app/composables/useAuth';
import { useAdminList, type AdminListFilters } from '@core/composables';
import { formatDate, roleVariant, userLabel } from '@app/admin/format';
import { useAdminLabels } from '@app/admin/useAdminLabels';
import { useListUsersAdminUsersGet } from '@gen/hooks/useListUsersAdminUsersGet';
import type { AdminUserListItem } from '@gen/models/AdminUserListItem';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import AdminFilterBar from '@app/presentation/components/admin/AdminFilterBar.vue';
import AdminDataTable, {
  type AdminColumn,
} from '@app/presentation/components/admin/AdminDataTable.vue';

/**
 * AdminUsers — searchable/filterable user list. Built on the shared admin stack
 * (AdminFilterBar → useAdminList → the generated `list_users` hook →
 * AdminDataTable). A row (a card on phones) opens the per-user detail page.
 */
const { t } = useI18n();
const router = useRouter();
const { isAdminOrOwner } = useAuth();
const { roleLabel, userTypeLabel } = useAdminLabels();

const list = useAdminList({ sortBy: 'created_at', sortDir: 'desc' });

const { data, isLoading, error, refetch } = useListUsersAdminUsersGet(list.params, {
  query: {
    enabled: () => isAdminOrOwner.value,
    staleTime: 30 * 1000,
  },
});

const rows = computed<AdminUserListItem[]>(() => data.value?.items ?? []);
const totalPages = computed(() => data.value?.total_pages ?? 1);
const total = computed(() => data.value?.total ?? 0);

const columns = computed<AdminColumn[]>(() => [
  { key: 'username', label: t('admin.users.columns.user'), sortable: true },
  { key: 'role', label: t('admin.users.columns.role'), sortable: true },
  { key: 'telegram_id', label: t('admin.users.columns.telegram') },
  { key: 'created_at', label: t('admin.users.columns.joined'), sortable: true },
]);

// Selects can't hold `undefined`, so 'all' stands for "no filter".
const roleFilter = computed({
  get: () => (list.filters.value.role as string) ?? 'all',
  set: (value: string) =>
    list.setFilters({ ...list.filters.value, role: value === 'all' ? undefined : value }),
});

const typeFilter = computed({
  get: () => (list.filters.value.user_type as string) ?? 'all',
  set: (value: string) =>
    list.setFilters({ ...list.filters.value, user_type: value === 'all' ? undefined : value }),
});

const onFilters = (next: AdminListFilters) => list.setFilters(next);

const openUser = (row: AdminUserListItem) => {
  void router.push({ name: 'admin-user-detail', params: { id: row.id } });
};
</script>

<template>
  <div class="flex flex-col gap-4">
    <p class="text-sm text-muted-foreground">{{ t('admin.users.description') }}</p>

    <AdminFilterBar
      :filters="list.filters.value"
      @update:filters="onFilters"
    >
      <div class="grid w-full grid-cols-2 gap-3 sm:flex sm:w-auto">
        <div class="flex min-w-0 flex-col gap-1">
          <Label
            for="admin-users-role"
            class="text-xs text-muted-foreground"
          >
            {{ t('admin.users.roleFilter') }}
          </Label>
          <Select v-model="roleFilter">
            <SelectTrigger
              id="admin-users-role"
              class="w-full sm:w-36"
            >
              <SelectValue :placeholder="t('admin.users.allRoles')" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{{ t('admin.users.allRoles') }}</SelectItem>
              <SelectItem value="user">{{ t('admin.users.role.user') }}</SelectItem>
              <SelectItem value="admin">{{ t('admin.users.role.admin') }}</SelectItem>
              <SelectItem value="owner">{{ t('admin.users.role.owner') }}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="flex min-w-0 flex-col gap-1">
          <Label
            for="admin-users-type"
            class="text-xs text-muted-foreground"
          >
            {{ t('admin.users.typeFilter') }}
          </Label>
          <Select v-model="typeFilter">
            <SelectTrigger
              id="admin-users-type"
              class="w-full sm:w-36"
            >
              <SelectValue :placeholder="t('admin.users.allTypes')" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{{ t('admin.users.allTypes') }}</SelectItem>
              <SelectItem value="REGISTERED">{{ t('admin.users.type.registered') }}</SelectItem>
              <SelectItem value="GUEST">{{ t('admin.users.type.guest') }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </AdminFilterBar>

    <AdminDataTable
      :columns="columns"
      :rows="rows"
      :is-loading="isLoading"
      :error="error"
      :sort-by="list.sortBy.value"
      :sort-dir="list.sortDir.value"
      :page="list.page.value"
      :total-pages="totalPages"
      :total="total"
      clickable-rows
      @sort="list.setSort"
      @retry="refetch()"
      @prev="list.prevPage"
      @next="list.nextPage"
      @row-click="openUser"
    >
      <template #cell-username="{ row }">
        <RouterLink
          :to="{ name: 'admin-user-detail', params: { id: row.id } }"
          class="font-medium hover:underline"
        >
          {{ userLabel(row) }}
        </RouterLink>
        <span
          v-if="row.user_type === 'GUEST'"
          class="ml-1.5 text-xs font-normal text-muted-foreground"
        >
          {{ userTypeLabel(row.user_type) }}
        </span>
      </template>
      <template #cell-role="{ row }">
        <Badge :variant="roleVariant(row.role)">{{ roleLabel(row.role) }}</Badge>
      </template>
      <template #cell-telegram_id="{ row }">
        <span class="text-xs tabular-nums text-muted-foreground">{{ row.telegram_id ?? '—' }}</span>
      </template>
      <template #cell-created_at="{ row }">
        <span class="whitespace-nowrap text-muted-foreground">{{ formatDate(row.created_at) }}</span>
      </template>
    </AdminDataTable>
  </div>
</template>
