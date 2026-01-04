<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { onlineManager } from '@tanstack/vue-query'
import { useI18n } from 'vue-i18n'
import { Wifi, WifiOff } from 'lucide-vue-next'

import { isApiError, getErrorMessage } from '@core/errors'
import { useGetServerTimeDemoTimeGet } from '@/gen/hooks'
import DemoSection from './DemoSection.vue'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'

const { t } = useI18n()
const isOnline = ref(true)
const simulatedOffline = ref(false)

const { data, error, isFetching, isError, refetch, isPaused } = useGetServerTimeDemoTimeGet({
  query: {
    retry: 2,
    retryDelay: 1000,
  },
})

let unsubscribe: (() => void) | null = null

onMounted(() => {
  unsubscribe = onlineManager.subscribe((online) => {
    isOnline.value = online
  })
  isOnline.value = onlineManager.isOnline()
})

onUnmounted(() => {
  unsubscribe?.()
})

const toggleSimulatedOffline = () => {
  const newState = !simulatedOffline.value
  simulatedOffline.value = newState
  onlineManager.setOnline(!newState)
}

// Extract ApiError properties
const apiError = computed(() => (isApiError(error.value) ? error.value : null))

const statusColor = computed(() => {
  if (simulatedOffline.value || !isOnline.value) return 'text-red-500'
  if (isFetching.value) return 'text-blue-500'
  if (isError.value) return 'text-yellow-500'
  return 'text-green-500'
})

const statusText = computed(() => {
  if (simulatedOffline.value) return t('demo.network.simulatedOffline')
  if (!isOnline.value) return t('demo.network.offline')
  if (isPaused.value) return t('demo.network.paused')
  if (isFetching.value) return t('demo.network.fetching')
  if (isError.value) return t('demo.network.error')
  return t('demo.network.online')
})
</script>

<template>
  <DemoSection icon="&#128225;" :title="t('demo.network.title')">
    <div class="space-y-4">
      <div class="flex items-center gap-4 flex-wrap">
        <div class="flex items-center gap-2" :class="statusColor">
          <span
            class="w-2 h-2 rounded-full"
            :class="isOnline && !simulatedOffline ? 'bg-green-500 animate-pulse' : 'bg-red-500'"
          />
          <Wifi
            v-if="isOnline && !simulatedOffline"
            class="w-5 h-5 motion-preset-pulse motion-duration-[2s] motion-loop-infinite"
          />
          <WifiOff v-else class="w-5 h-5 motion-preset-shake motion-duration-[0.5s]" />
          <span class="font-medium">{{ statusText }}</span>
        </div>

        <!-- Show error classification when offline -->
        <Badge v-if="simulatedOffline || !isOnline" variant="outline" class="text-xs font-mono">
          classifies as: OFFLINE
        </Badge>
      </div>

      <div class="bg-muted rounded-lg p-4">
        <div v-if="isPaused" class="space-y-3">
          <Alert class="motion-preset-slide-up-sm motion-preset-fade motion-duration-[0.3s]">
            <AlertDescription class="flex items-center justify-between">
              <span>{{ t('demo.network.queryPaused') }}</span>
              <span class="text-xs text-muted-foreground">
                {{ t('demo.network.willRetryWhenOnline') }}
              </span>
            </AlertDescription>
          </Alert>

          <!-- Network error classification info -->
          <div class="bg-background/50 rounded-md p-3 text-xs font-mono space-y-1 border">
            <div class="text-muted-foreground mb-2 font-sans text-xs font-medium">
              Network Error Classification:
            </div>
            <div class="flex items-center gap-2">
              <span class="text-muted-foreground">code:</span>
              <Badge variant="secondary" class="text-xs h-5">OFFLINE</Badge>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-muted-foreground">recoverable:</span>
              <Badge variant="default" class="text-xs h-5">true</Badge>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-muted-foreground">behavior:</span>
              <span class="text-foreground">Query paused, auto-resumes</span>
            </div>
          </div>
        </div>
        <div v-else-if="isError" class="space-y-3">
          <Alert variant="destructive" class="motion-preset-shake motion-duration-[0.4s]">
            <AlertDescription>{{ getErrorMessage(error) }}</AlertDescription>
          </Alert>

          <!-- Show ApiError properties if available -->
          <div v-if="apiError" class="bg-background/50 rounded-md p-3 text-xs font-mono space-y-1 border">
            <div class="text-muted-foreground mb-2 font-sans text-xs font-medium">
              ApiError Properties:
            </div>
            <div class="flex items-center gap-2">
              <span class="text-muted-foreground">status:</span>
              <Badge variant="secondary" class="text-xs h-5">
                {{ apiError.status }}
              </Badge>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-muted-foreground">recoverable:</span>
              <Badge :variant="apiError.recoverable ? 'default' : 'secondary'" class="text-xs h-5">
                {{ String(apiError.recoverable) }}
              </Badge>
            </div>
          </div>
        </div>
        <div v-else class="text-center">
          <p :key="data?.formatted" class="text-2xl font-mono font-bold motion-preset-pop motion-duration-[0.2s]">
            {{ data?.formatted ?? '--:--:--' }}
          </p>
          <p class="text-xs text-muted-foreground mt-1">
            {{ t('demo.network.serverTime') }}
          </p>
        </div>
      </div>

      <div class="flex gap-2 flex-wrap">
        <Button
          :variant="simulatedOffline ? 'destructive' : 'outline'"
          class="active:scale-95 hover:-translate-y-0.5 hover:shadow-md transition-all duration-150"
          @click="toggleSimulatedOffline"
        >
          <WifiOff v-if="simulatedOffline" class="w-4 h-4 mr-2" />
          <Wifi v-else class="w-4 h-4 mr-2" />
          {{ simulatedOffline ? t('demo.network.goOnline') : t('demo.network.simulateOffline') }}
        </Button>
        <Button
          variant="outline"
          :disabled="isFetching || simulatedOffline"
          class="active:scale-95 hover:-translate-y-0.5 hover:shadow-md transition-all duration-150"
          @click="refetch()"
        >
          {{ t('demo.network.refetch') }}
        </Button>
      </div>

      <p class="text-xs text-muted-foreground">{{ t('demo.network.note') }}</p>
    </div>
  </DemoSection>
</template>
