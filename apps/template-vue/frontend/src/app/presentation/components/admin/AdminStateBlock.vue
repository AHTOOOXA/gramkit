<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';

/**
 * AdminStateBlock — the canonical async-state wrapper for every admin section.
 *
 * Branch order is fixed and exact: isLoading → error → empty → default slot.
 * (A failed refetch that still has stale data is treated as an error here so
 * the retry affordance is always reachable.)
 *
 * Slots: #loading (optional custom skeleton), #empty (optional placeholder),
 * default (the data). Emits `retry` from the error Alert's retry button.
 *
 * TODO: extract to core when a third Vue app needs this (each Vue app keeps
 * its own copy for now, built on its own `ui/*` kit).
 */
withDefaults(
  defineProps<{
    isLoading?: boolean;
    error?: unknown;
    isEmpty?: boolean;
    /** How many skeleton rows the default loading state renders. */
    skeletonRows?: number;
  }>(),
  { isLoading: false, error: undefined, isEmpty: false, skeletonRows: 5 },
);

const emit = defineEmits<{ retry: [] }>();

const { t } = useI18n();
</script>

<template>
  <!-- 1. Loading -->
  <div v-if="isLoading">
    <slot name="loading">
      <div class="space-y-2">
        <Skeleton
          v-for="i in skeletonRows"
          :key="i"
          class="h-10 w-full"
        />
      </div>
    </slot>
  </div>

  <!-- 2. Error -->
  <Alert
    v-else-if="error"
    variant="destructive"
    class="motion-preset-shake motion-duration-[0.4s]"
  >
    <AlertDescription class="flex items-center justify-between gap-3">
      <span>{{ t('admin.state.error') }}</span>
      <Button
        size="sm"
        variant="outline"
        @click="emit('retry')"
      >
        {{ t('admin.state.retry') }}
      </Button>
    </AlertDescription>
  </Alert>

  <!-- 3. Empty -->
  <div v-else-if="isEmpty">
    <slot name="empty">
      <div
        class="flex flex-col items-center justify-center rounded-xl border border-dashed border-border py-12 text-center text-sm text-muted-foreground"
      >
        {{ t('admin.state.empty') }}
      </div>
    </slot>
  </div>

  <!-- 4. Data -->
  <slot v-else />
</template>
