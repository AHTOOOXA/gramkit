<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { watchDebounced } from '@vueuse/core';
import { useI18n } from 'vue-i18n';
import { Search } from '@lucide/vue';
import type { AdminListFilters } from '@core/composables';
import { Input } from '@/components/ui/input';
import DateRangePicker, { type DateRange } from './DateRangePicker.vue';

/**
 * AdminFilterBar — free-text search + a date range over an `AdminListFilters`
 * bag (the same shape `useAdminList` owns). Section filters (e.g. an `action`
 * Select) go in the default slot; the parent merges them into the same object.
 *
 * Mobile-first: search takes the full row, slot filters and the two dates wrap
 * below it; from `sm` up everything sits on one wrapping line.
 *
 * TODO: extract to core when a third Vue app needs this (each Vue app keeps
 * its own copy for now, built on its own `ui/*` kit).
 */
const props = withDefaults(defineProps<{ filters?: AdminListFilters; searchable?: boolean }>(), {
  filters: () => ({}),
  searchable: true,
});

const emit = defineEmits<{ 'update:filters': [value: AdminListFilters] }>();

const { t } = useI18n();

// Debounced: every keystroke would otherwise refetch the list (+ its count query)
// and reset the page. The local value follows outside changes (e.g. a URL reset).
const search = ref(props.filters?.search ?? '');
watch(
  () => props.filters?.search ?? '',
  (value) => {
    if (value !== search.value) search.value = value;
  },
);
watchDebounced(
  search,
  (value) => {
    if (value !== (props.filters?.search ?? '')) {
      emit('update:filters', { ...props.filters, search: value });
    }
  },
  { debounce: 300 },
);

const dateRange = computed<DateRange>({
  get: () => ({ from: props.filters?.date_from, to: props.filters?.date_to }),
  set: (value: DateRange) =>
    emit('update:filters', { ...props.filters, date_from: value.from, date_to: value.to }),
});
</script>

<template>
  <div class="flex flex-wrap items-end gap-3 rounded-xl border border-border bg-card p-3">
    <div
      v-if="searchable"
      class="relative w-full sm:w-auto sm:min-w-[12rem] sm:flex-1"
    >
      <Search
        class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
      />
      <Input
        v-model="search"
        type="search"
        :placeholder="t('admin.filters.searchPlaceholder')"
        class="pl-9"
      />
    </div>

    <!-- Section-specific Selects (e.g. action filter) go here. -->
    <slot />

    <DateRangePicker v-model="dateRange" />
  </div>
</template>
