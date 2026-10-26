<script setup lang="ts" generic="T extends Record<string, unknown>">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { ArrowDown, ArrowUp, ChevronsUpDown } from '@lucide/vue';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';
import AdminStateBlock from './AdminStateBlock.vue';
import AdminPagination from './AdminPagination.vue';

export interface AdminColumn {
  /** Stable key — also the cell slot name (`cell-<key>`) and sort column id. */
  key: string;
  /** Header label (already translated by the caller). An empty label marks an
   *  actions column: on phones it sits next to the card title. */
  label: string;
  /** Enable click-to-sort on this column header. */
  sortable?: boolean;
  /** Extra classes for the cell + header (alignment, width). */
  class?: string;
  /** What the column means — shown on hovering the header (dotted underline marks it). */
  hint?: string;
}

/**
 * AdminDataTable — the shared table for every admin list. Wraps shadcn `Table`
 * with sortable headers, per-column cell slots (`#cell-<key>`), and a controlled
 * pagination footer, all behind `AdminStateBlock` (loading → error → empty →
 * data). Designed to pair with `useAdminList`.
 *
 * Below `md` (phones, Telegram) each row renders as a card instead: the first
 * column is the card title, the rest are label/value pairs, and sorting moves
 * to a compact Select + direction toggle. Both layouts use the same cell slots.
 *
 * TODO: extract to core when a third Vue app needs this (each Vue app keeps
 * its own copy for now, built on its own `ui/*` kit).
 */
const props = withDefaults(
  defineProps<{
    columns: AdminColumn[];
    rows: T[];
    rowKey?: keyof T | ((row: T) => string | number);
    isLoading?: boolean;
    error?: unknown;
    sortBy?: string | null;
    sortDir?: 'asc' | 'desc';
    page?: number;
    totalPages?: number;
    total?: number;
    /** Smaller text and tighter cells, for wide tables with many columns. */
    dense?: boolean;
    /** Hide the pagination footer (for short, unpaginated lists). */
    hidePagination?: boolean;
    /** Make whole rows (cards on phones) clickable; clicks emit `rowClick`. */
    clickableRows?: boolean;
  }>(),
  {
    rowKey: undefined,
    isLoading: false,
    error: undefined,
    sortBy: null,
    sortDir: 'desc',
    page: 1,
    totalPages: 1,
    total: undefined,
    dense: false,
    hidePagination: false,
    clickableRows: false,
  },
);

const emit = defineEmits<{
  sort: [column: string];
  retry: [];
  prev: [];
  next: [];
  rowClick: [row: T];
}>();

const { t } = useI18n();

const isEmpty = computed(() => !props.isLoading && !props.error && props.rows.length === 0);

const sortableColumns = computed(() => props.columns.filter((c) => c.sortable));
const titleColumn = computed(() => props.columns[0]);
const fieldColumns = computed(() => props.columns.slice(1).filter((c) => c.label));
const actionColumns = computed(() => props.columns.slice(1).filter((c) => !c.label));

const resolveRowKey = (row: T, index: number): string | number => {
  if (typeof props.rowKey === 'function') return props.rowKey(row);
  // Default to an `id` column when no rowKey prop is given, else the index.
  const key = props.rowKey ?? ('id' as keyof T);
  const value = row[key];
  return (value as string | number | undefined) ?? index;
};

// Clicks on links/buttons/menus inside a row keep their own behaviour.
const onRowClick = (row: T, event: MouseEvent) => {
  if (!props.clickableRows) return;
  if ((event.target as HTMLElement | null)?.closest('a, button, [role="menuitem"], input')) return;
  emit('rowClick', row);
};

const onHeaderClick = (column: AdminColumn) => {
  if (column.sortable) emit('sort', column.key);
};

// Mobile sort control. `setSort` in useAdminList toggles the direction when the
// same column comes in again, so both controls just emit `sort`.
const mobileSort = computed({
  get: () => props.sortBy ?? '',
  set: (value: string) => {
    if (value && value !== props.sortBy) emit('sort', value);
  },
});
const toggleDir = () => {
  if (props.sortBy) emit('sort', props.sortBy);
};
</script>

<template>
  <div>
    <AdminStateBlock
      :is-loading="isLoading"
      :error="error"
      :is-empty="isEmpty"
      @retry="emit('retry')"
    >
      <!-- Forward an optional custom empty placeholder to AdminStateBlock. -->
      <template
        v-if="$slots.empty"
        #empty
      >
        <slot name="empty" />
      </template>

      <!-- Phones: sort control + one card per row -->
      <div class="flex flex-col gap-2 md:hidden">
        <div
          v-if="sortableColumns.length"
          class="flex items-center gap-2"
        >
          <span class="shrink-0 text-xs text-muted-foreground">{{ t('admin.table.sortBy') }}</span>
          <Select v-model="mobileSort">
            <SelectTrigger
              size="sm"
              class="min-w-0 flex-1"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem
                v-for="column in sortableColumns"
                :key="column.key"
                :value="column.key"
              >
                {{ column.label }}
              </SelectItem>
            </SelectContent>
          </Select>
          <Button
            size="icon-sm"
            variant="outline"
            :disabled="!sortBy"
            :aria-label="t('admin.table.sortDir')"
            @click="toggleDir"
          >
            <ArrowUp
              v-if="sortDir === 'asc'"
              class="h-4 w-4"
            />
            <ArrowDown
              v-else
              class="h-4 w-4"
            />
          </Button>
        </div>

        <ul class="flex flex-col gap-2">
          <li
            v-for="(row, index) in rows"
            :key="resolveRowKey(row, index)"
            :class="cn(
              'rounded-xl border border-border bg-card p-3 text-sm',
              clickableRows && 'cursor-pointer transition-colors active:bg-muted/50',
            )"
            @click="onRowClick(row, $event)"
          >
            <div class="mb-2 flex items-start justify-between gap-2">
              <div
                v-if="titleColumn"
                class="min-w-0 break-words py-0.5 font-medium"
              >
                <slot
                  :name="`cell-${titleColumn.key}`"
                  :row="row"
                  :value="row[titleColumn.key]"
                >
                  {{ row[titleColumn.key] }}
                </slot>
              </div>
              <div
                v-for="column in actionColumns"
                :key="column.key"
                class="-my-1 -mr-1 shrink-0 empty:hidden"
              >
                <slot
                  :name="`cell-${column.key}`"
                  :row="row"
                  :value="row[column.key]"
                />
              </div>
            </div>
            <dl class="grid grid-cols-[minmax(0,auto)_minmax(0,1fr)] gap-x-3 gap-y-1.5">
              <template
                v-for="column in fieldColumns"
                :key="column.key"
              >
                <dt class="text-xs leading-5 text-muted-foreground">{{ column.label }}</dt>
                <dd class="min-w-0 break-words">
                  <slot
                    :name="`cell-${column.key}`"
                    :row="row"
                    :value="row[column.key]"
                  >
                    {{ row[column.key] }}
                  </slot>
                </dd>
              </template>
            </dl>
          </li>
        </ul>
      </div>

      <!-- md and up: the table -->
      <div class="hidden overflow-x-auto rounded-xl border border-border md:block">
        <Table :class="dense && 'text-xs'">
          <TableHeader>
            <TableRow>
              <TableHead
                v-for="column in columns"
                :key="column.key"
                :class="cn(column.sortable && 'cursor-pointer select-none', dense && 'h-8 px-1.5', column.class)"
                :title="column.hint"
                @click="onHeaderClick(column)"
              >
                <span class="inline-flex items-center gap-1">
                  <span :class="column.hint && 'underline decoration-dotted underline-offset-4'">{{ column.label }}</span>
                  <template v-if="column.sortable">
                    <ArrowUp
                      v-if="sortBy === column.key && sortDir === 'asc'"
                      class="h-3.5 w-3.5"
                    />
                    <ArrowDown
                      v-else-if="sortBy === column.key && sortDir === 'desc'"
                      class="h-3.5 w-3.5"
                    />
                    <ChevronsUpDown
                      v-else
                      class="h-3.5 w-3.5 text-muted-foreground/50"
                    />
                  </template>
                </span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="(row, index) in rows"
              :key="resolveRowKey(row, index)"
              :class="clickableRows && 'cursor-pointer'"
              @click="onRowClick(row, $event)"
            >
              <TableCell
                v-for="column in columns"
                :key="column.key"
                :class="cn(dense && 'px-1.5 py-1.5', column.class)"
              >
                <slot
                  :name="`cell-${column.key}`"
                  :row="row"
                  :value="row[column.key]"
                >
                  {{ row[column.key] }}
                </slot>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>

      <AdminPagination
        v-if="!hidePagination"
        :page="page"
        :total-pages="totalPages"
        :total="total"
        @prev="emit('prev')"
        @next="emit('next')"
      />
    </AdminStateBlock>
  </div>
</template>
