<script setup lang="ts">
import { ref, computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { useI18n } from 'vue-i18n'

import { getServerTimeDemoTimeGet } from '@/gen/client'
import DemoSection from './DemoSection.vue'
import { Button } from '@/components/ui/button'

const POLL_INTERVALS = [
  { label: 'Off', value: 0 },
  { label: '1s', value: 1000 },
  { label: '2s', value: 2000 },
  { label: '5s', value: 5000 },
]

const { t } = useI18n()
const pollInterval = ref(0)

// Computed for reactive refetchInterval
const refetchInterval = computed(() => (pollInterval.value > 0 ? pollInterval.value : false))

// Use useQuery directly for reactive refetchInterval support
const { data, isFetching, dataUpdatedAt } = useQuery({
  queryKey: ['demo', 'server-time'],
  queryFn: () => getServerTimeDemoTimeGet(),
  refetchInterval,
})

const formatTime = (timestamp: number) => new Date(timestamp).toLocaleTimeString()
</script>

<template>
  <DemoSection icon="&#128260;" :title="t('demo.polling.title')">
    <div class="space-y-4">
      <div class="flex items-center gap-4 text-sm">
        <span>
          <span class="font-mono">polling:</span>
          <span :class="pollInterval > 0 ? 'text-green-500' : 'text-muted-foreground'">
            {{ pollInterval > 0 ? `${pollInterval}ms` : 'off' }}
          </span>
        </span>
        <span>
          <span class="font-mono">isFetching:</span>
          <span :class="isFetching ? 'text-blue-500' : 'text-muted-foreground'">
            {{ String(isFetching) }}
          </span>
        </span>
      </div>

      <div class="bg-muted rounded-lg p-4">
        <div class="text-center">
          <p
            class="text-4xl font-mono font-bold transition-all duration-150"
            :class="isFetching ? 'opacity-50 scale-95' : 'opacity-100 scale-100'"
          >
            {{ data?.formatted ?? '--:--:--' }}
          </p>
          <p class="text-xs text-muted-foreground mt-2">
            {{ t('demo.polling.serverTime') }}
          </p>
          <p v-if="dataUpdatedAt" class="text-xs text-muted-foreground">
            {{ t('demo.polling.lastUpdate') }}: {{ formatTime(dataUpdatedAt) }}
          </p>
        </div>
      </div>

      <div class="flex gap-2 flex-wrap">
        <Button
          v-for="interval in POLL_INTERVALS"
          :key="interval.value"
          :variant="pollInterval === interval.value ? 'default' : 'outline'"
          size="sm"
          class="active:scale-95 transition-transform duration-100"
          @click="pollInterval = interval.value"
        >
          {{ interval.label }}
        </Button>
      </div>

      <p class="text-xs text-muted-foreground">{{ t('demo.polling.note') }}</p>
    </div>
  </DemoSection>
</template>
