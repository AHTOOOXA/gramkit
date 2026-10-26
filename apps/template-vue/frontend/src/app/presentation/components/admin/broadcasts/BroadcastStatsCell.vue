<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import type { BroadcastDeliveryStats } from '@gen/models/BroadcastDeliveryStats';

/**
 * BroadcastStatsCell — compact delivery counters for a broadcast (list rows and
 * the detail page).
 *
 * Telegram exposes neither read receipts nor clicks, so this only shows
 * sent / success / fail / cycles (never a fabricated CTR).
 *
 * TODO: extract to core when a third Vue app needs this (each Vue app keeps
 * its own copy for now, built on its own `ui/*` kit).
 */
const props = defineProps<{ stats: BroadcastDeliveryStats }>();

const { t } = useI18n();

const successRate = computed(() => {
  const sent = props.stats.sent_count;
  if (!sent) return null;
  return Math.round((props.stats.success_count / sent) * 100);
});
</script>

<template>
  <div class="flex flex-col gap-0.5 text-xs">
    <span v-if="stats.cycles_run === 0" class="text-muted-foreground">
      {{ t('admin.broadcasts.stats.notSentYet') }}
    </span>
    <template v-else>
      <span class="text-foreground">
        {{ t('admin.broadcasts.stats.delivered') }}: {{ stats.success_count }}/{{ stats.sent_count }}
        <span v-if="successRate !== null" class="text-muted-foreground">({{ successRate }}%)</span>
      </span>
      <span v-if="stats.fail_count > 0" class="text-destructive">
        {{ t('admin.broadcasts.stats.failed') }}: {{ stats.fail_count }}
      </span>
      <span class="text-muted-foreground">
        {{ t('admin.broadcasts.stats.cycles') }}: {{ stats.cycles_run }}
      </span>
    </template>
  </div>
</template>
