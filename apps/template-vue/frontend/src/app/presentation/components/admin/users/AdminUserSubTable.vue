<script setup lang="ts" generic="T extends Record<string, unknown>">
import AdminDataTable, {
  type AdminColumn,
} from '@app/presentation/components/admin/AdminDataTable.vue';

/**
 * AdminUserSubTable — a labelled wrapper around AdminDataTable for the
 * per-user sub-lists on the detail page (payments / subscriptions / whatever
 * an app panel lists). The parent owns the query (via useAdminList + a
 * generated hook) and passes rows + pagination state down; this just frames it
 * and re-exposes the table's `#cell-<key>` slots so callers can render custom
 * cells.
 *
 * TODO: extract to core when a third Vue app needs this (each Vue app keeps
 * its own copy for now, built on its own `ui/*` kit).
 */
withDefaults(
  defineProps<{
    /** Optional heading; the detail page's tab label usually names the list already. */
    title?: string;
    columns: AdminColumn[];
    rows: T[];
    isLoading?: boolean;
    error?: unknown;
    sortBy?: string | null;
    sortDir?: 'asc' | 'desc';
    page?: number;
    totalPages?: number;
    total?: number;
    hidePagination?: boolean;
  }>(),
  {
    title: undefined,
    isLoading: false,
    error: undefined,
    sortBy: null,
    sortDir: 'desc',
    page: 1,
    totalPages: 1,
    total: undefined,
    hidePagination: false,
  },
);

const emit = defineEmits<{
  sort: [column: string];
  retry: [];
  prev: [];
  next: [];
}>();
</script>

<template>
  <section class="flex flex-col gap-2">
    <h3
      v-if="title"
      class="text-sm font-semibold"
    >
      {{ title }}
    </h3>
    <AdminDataTable
      :columns="columns"
      :rows="rows"
      :is-loading="isLoading"
      :error="error"
      :sort-by="sortBy"
      :sort-dir="sortDir"
      :page="page"
      :total-pages="totalPages"
      :total="total"
      :hide-pagination="hidePagination"
      @sort="emit('sort', $event)"
      @retry="emit('retry')"
      @prev="emit('prev')"
      @next="emit('next')"
    >
      <!-- Re-expose every cell slot the caller passes through. -->
      <template
        v-for="(_, name) in $slots"
        #[name]="slotProps"
      >
        <slot
          :name="name"
          v-bind="slotProps"
        />
      </template>
    </AdminDataTable>
  </section>
</template>
