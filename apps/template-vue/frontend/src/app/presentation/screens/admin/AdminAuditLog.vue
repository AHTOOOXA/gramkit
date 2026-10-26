<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { Download } from '@lucide/vue';
import { useAuth } from '@app/composables/useAuth';
import { useAdminList, useCsvExport, type AdminListFilters } from '@core/composables';
import { formatDate } from '@app/admin/format';
import { useAdminLabels } from '@app/admin/useAdminLabels';
import { useListAuditLogAdminAuditLogGet } from '@gen/hooks/useListAuditLogAdminAuditLogGet';
import { useListAuditActionsAdminAuditLogActionsGet } from '@gen/hooks/useListAuditActionsAdminAuditLogActionsGet';
import type { AuditLogSchema } from '@gen/models/AuditLogSchema';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import AdminFilterBar from '@app/presentation/components/admin/AdminFilterBar.vue';
import AdminDataTable, {
  type AdminColumn,
} from '@app/presentation/components/admin/AdminDataTable.vue';

/**
 * AdminAuditLog — the trail of mutating admin/owner actions: AdminFilterBar
 * (search + action filter + date range) → useAdminList → the generated
 * `list_audit_log` hook → AdminDataTable, with CSV export of the current page.
 * The action Select lists every action recorded so far (`/admin/audit-log/actions`).
 * Empty until something writes audit rows; the empty state is expected.
 * `?action=<action>` pre-selects the action filter (the Tasks section's
 * "Run history" link uses it); the filters aren't synced back to the URL.
 */
const { t } = useI18n();
const { isAdminOrOwner } = useAuth();
const { roleLabel } = useAdminLabels();
const { exportCsv } = useCsvExport();

const list = useAdminList({ sortBy: 'created_at', sortDir: 'desc' });

// Seed the action filter once from the URL, before the first fetch.
const initialAction = useRoute().query.action;
if (typeof initialAction === 'string' && initialAction) {
  list.setFilters({ ...list.filters.value, action: initialAction });
}

const { data, isLoading, error, refetch } = useListAuditLogAdminAuditLogGet(list.params, {
  query: {
    enabled: () => isAdminOrOwner.value,
    staleTime: 30 * 1000,
  },
});

const { data: actions } = useListAuditActionsAdminAuditLogActionsGet({
  query: {
    enabled: () => isAdminOrOwner.value,
    staleTime: 5 * 60 * 1000,
  },
});

// The seeded `?action=` may not be recorded yet (a task nobody has run), so it
// isn't in `/actions`; keep it selectable so the Select shows the active filter.
const actionOptions = computed<string[]>(() => {
  const known = actions.value ?? [];
  const current = list.filters.value.action as string | undefined;
  return current && !known.includes(current) ? [current, ...known] : known;
});

const rows = computed<AuditLogSchema[]>(() => data.value?.items ?? []);
const totalPages = computed(() => data.value?.total_pages ?? 1);
const total = computed(() => data.value?.total ?? 0);

const columns = computed<AdminColumn[]>(() => [
  { key: 'action', label: t('admin.auditLog.columns.action'), sortable: true },
  { key: 'actor', label: t('admin.auditLog.columns.actor') },
  { key: 'target', label: t('admin.auditLog.columns.target') },
  { key: 'created_at', label: t('admin.auditLog.columns.date'), sortable: true },
  { key: 'detail', label: t('admin.auditLog.columns.detail') },
]);

// Selects can't hold `undefined`, so 'all' stands for "no filter".
const actionFilter = computed({
  get: () => (list.filters.value.action as string) ?? 'all',
  set: (value: string) =>
    list.setFilters({ ...list.filters.value, action: value === 'all' ? undefined : value }),
});

const onFilters = (next: AdminListFilters) => list.setFilters(next);

const actorLabel = (row: AuditLogSchema): string =>
  row.actor_username ?? (row.actor_telegram_id ? `#${row.actor_telegram_id}` : '—');

const targetLabel = (row: AuditLogSchema): string => {
  if (!row.target_type && !row.target_id) return '—';
  return [row.target_type, row.target_id].filter(Boolean).join(':');
};

const detailLabel = (row: AuditLogSchema): string =>
  row.detail ? JSON.stringify(row.detail) : '—';

const onExport = () => {
  exportCsv(
    rows.value,
    [
      { header: t('admin.auditLog.columns.action'), accessor: (r) => r.action },
      { header: t('admin.auditLog.columns.actor'), accessor: (r) => actorLabel(r) },
      { header: t('admin.users.columns.role'), accessor: (r) => r.actor_role },
      { header: t('admin.auditLog.columns.target'), accessor: (r) => targetLabel(r) },
      { header: t('admin.auditLog.columns.date'), accessor: (r) => r.created_at },
      { header: t('admin.auditLog.columns.detail'), accessor: (r) => r.detail },
    ],
    'audit-log',
  );
};
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <p class="text-sm text-muted-foreground">{{ t('admin.auditLog.description') }}</p>
      <Button
        size="sm"
        variant="outline"
        class="w-fit shrink-0"
        :disabled="!rows.length"
        @click="onExport"
      >
        <Download class="h-4 w-4" />
        {{ t('admin.table.exportCsv') }}
      </Button>
    </div>

    <AdminFilterBar
      :filters="list.filters.value"
      @update:filters="onFilters"
    >
      <div class="flex w-full min-w-0 flex-col gap-1 sm:w-auto">
        <Label
          for="admin-audit-action"
          class="text-xs text-muted-foreground"
        >
          {{ t('admin.auditLog.actionFilter') }}
        </Label>
        <Select v-model="actionFilter">
          <SelectTrigger
            id="admin-audit-action"
            class="w-full sm:w-48"
          >
            <SelectValue :placeholder="t('admin.auditLog.allActions')" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{{ t('admin.auditLog.allActions') }}</SelectItem>
            <SelectItem
              v-for="action in actionOptions"
              :key="action"
              :value="action"
            >
              {{ action }}
            </SelectItem>
          </SelectContent>
        </Select>
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
      @sort="list.setSort"
      @retry="refetch()"
      @prev="list.prevPage"
      @next="list.nextPage"
    >
      <template #cell-action="{ row }">
        <span class="font-mono text-[13px] font-medium">{{ row.action }}</span>
      </template>
      <template #cell-actor="{ row }">
        <span>{{ actorLabel(row) }}</span>
        <span class="ml-1 text-xs text-muted-foreground">({{ roleLabel(row.actor_role) }})</span>
      </template>
      <template #cell-target="{ row }">
        <span class="break-all">{{ targetLabel(row) }}</span>
      </template>
      <template #cell-created_at="{ row }">
        <span class="whitespace-nowrap text-muted-foreground">{{ formatDate(row.created_at, true) }}</span>
      </template>
      <template #cell-detail="{ row }">
        <span
          class="line-clamp-2 break-all font-mono text-xs text-muted-foreground md:line-clamp-1 md:max-w-[18rem]"
          :title="detailLabel(row)"
        >
          {{ detailLabel(row) }}
        </span>
      </template>
    </AdminDataTable>
  </div>
</template>
