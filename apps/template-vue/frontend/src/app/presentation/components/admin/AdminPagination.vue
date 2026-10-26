<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { ChevronLeft, ChevronRight } from '@lucide/vue';
import { Button } from '@/components/ui/button';

/**
 * AdminPagination — controlled prev/next pager driven by `useAdminList`.
 * Stateless: it reads page / totalPages and emits intent; the parent wires
 * those to `nextPage()` / `prevPage()`. On narrow screens the buttons drop
 * their text and keep the chevrons (the label stays as `aria-label`).
 *
 * TODO: extract to core when a third Vue app needs this (each Vue app keeps
 * its own copy for now, built on its own `ui/*` kit).
 */
const props = defineProps<{
  page: number;
  totalPages: number;
  total?: number;
}>();

const emit = defineEmits<{ prev: []; next: [] }>();

const { t } = useI18n();

const canPrev = computed(() => props.page > 1);
const canNext = computed(() => props.page < props.totalPages);
</script>

<template>
  <div class="flex items-center justify-between gap-3 pt-3 text-sm">
    <span class="min-w-0 text-muted-foreground">
      {{ t('admin.table.pageOf', { page, total: Math.max(totalPages, 1) }) }}
      <template v-if="total !== undefined">
        <span class="whitespace-nowrap">· {{ t('admin.table.totalRows', { count: total }) }}</span>
      </template>
    </span>
    <div class="flex shrink-0 items-center gap-2">
      <Button
        size="sm"
        variant="outline"
        :disabled="!canPrev"
        :aria-label="t('admin.table.prev')"
        @click="emit('prev')"
      >
        <ChevronLeft class="h-4 w-4" />
        <span class="hidden sm:inline">{{ t('admin.table.prev') }}</span>
      </Button>
      <Button
        size="sm"
        variant="outline"
        :disabled="!canNext"
        :aria-label="t('admin.table.next')"
        @click="emit('next')"
      >
        <span class="hidden sm:inline">{{ t('admin.table.next') }}</span>
        <ChevronRight class="h-4 w-4" />
      </Button>
    </div>
  </div>
</template>
