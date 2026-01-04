<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuery } from '@tanstack/vue-query'
import { RefreshCw, XCircle, CheckCircle } from 'lucide-vue-next'

import { getErrorMessage } from '@core/errors'
import { triggerErrorDemoErrorStatusCodeGet } from '@/gen/client/triggerErrorDemoErrorStatusCodeGet'
import DemoSection from './DemoSection.vue'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

const { t } = useI18n()

interface AttemptLog {
  attempt: number
  timestamp: number
  status: 'pending' | 'failed' | 'success'
}

// State for tracking attempts
const attempts500 = ref<AttemptLog[]>([])
const attempts404 = ref<AttemptLog[]>([])
const active500 = ref(false)
const active404 = ref(false)

const attempt500Ref = ref(0)
const attempt404Ref = ref(0)

// Query for 500 error (will retry)
const query500 = useQuery({
  queryKey: ['demo-error-500', active500],
  queryFn: async () => {
    attempt500Ref.value += 1
    const currentAttempt = attempt500Ref.value

    attempts500.value.push({
      attempt: currentAttempt,
      timestamp: Date.now(),
      status: 'pending',
    })

    try {
      await triggerErrorDemoErrorStatusCodeGet(500)
      attempts500.value = attempts500.value.map((a) =>
        a.attempt === currentAttempt ? { ...a, status: 'success' as const } : a
      )
      return { success: true }
    } catch (error) {
      attempts500.value = attempts500.value.map((a) =>
        a.attempt === currentAttempt ? { ...a, status: 'failed' as const } : a
      )
      throw error
    }
  },
  enabled: () => active500.value,
  retry: 3,
  retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 5000),
})

// Query for 404 error (no retry)
const query404 = useQuery({
  queryKey: ['demo-error-404', active404],
  queryFn: async () => {
    attempt404Ref.value += 1
    const currentAttempt = attempt404Ref.value

    attempts404.value.push({
      attempt: currentAttempt,
      timestamp: Date.now(),
      status: 'pending',
    })

    try {
      await triggerErrorDemoErrorStatusCodeGet(404)
      attempts404.value = attempts404.value.map((a) =>
        a.attempt === currentAttempt ? { ...a, status: 'success' as const } : a
      )
      return { success: true }
    } catch (error) {
      attempts404.value = attempts404.value.map((a) =>
        a.attempt === currentAttempt ? { ...a, status: 'failed' as const } : a
      )
      throw error
    }
  },
  enabled: () => active404.value,
  // Uses default retry from QueryClient which checks recoverable
})

const trigger500 = () => {
  attempt500Ref.value = 0
  attempts500.value = []
  active500.value = true
}

const trigger404 = () => {
  attempt404Ref.value = 0
  attempts404.value = []
  active404.value = true
}

// Reset active state when queries settle
watch(
  () => query500.isFetching.value,
  (isFetching) => {
    if (!isFetching && active500.value) {
      setTimeout(() => {
        active500.value = false
      }, 500)
    }
  }
)

watch(
  () => query404.isFetching.value,
  (isFetching) => {
    if (!isFetching && active404.value) {
      setTimeout(() => {
        active404.value = false
      }, 500)
    }
  }
)
</script>

<template>
  <DemoSection icon="&#128260;" :title="t('demo.retryComparison.title')">
    <div class="space-y-4">
      <p class="text-sm text-muted-foreground">
        {{ t('demo.retryComparison.description') }}
      </p>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- 500 Error Panel -->
        <div class="flex-1 space-y-3">
          <div class="flex items-center justify-between">
            <h4 class="font-medium text-sm">{{ t('demo.retryComparison.serverError') }}</h4>
            <Badge variant="default" class="text-xs">
              {{ t('demo.retryComparison.willRetry') }}
            </Badge>
          </div>

          <div class="text-xs text-muted-foreground space-y-1">
            <div>
              <span class="font-mono">status:</span> 500
            </div>
            <div>
              <span class="font-mono">recoverable:</span> true
            </div>
          </div>

          <Button
            size="sm"
            variant="outline"
            :disabled="query500.isFetching.value"
            class="w-full active:scale-95 transition-transform"
            @click="trigger500"
          >
            <RefreshCw v-if="query500.isFetching.value" class="w-4 h-4 mr-2 animate-spin" />
            {{ t('demo.retryComparison.trigger') }}
          </Button>

          <!-- Timeline -->
          <div class="bg-muted/50 rounded-lg p-3 min-h-[140px] space-y-2">
            <div
              v-if="!active500 && attempts500.length === 0"
              class="text-xs text-muted-foreground text-center py-8"
            >
              {{ t('demo.retryComparison.clickToStart') }}
            </div>

            <div
              v-for="(attempt, idx) in attempts500"
              :key="idx"
              class="flex items-center gap-2 text-xs motion-preset-slide-right motion-duration-[0.2s]"
              :style="{ animationDelay: `${idx * 100}ms` }"
            >
              <RefreshCw v-if="attempt.status === 'pending'" class="w-3 h-3 text-blue-500 animate-spin" />
              <XCircle v-else-if="attempt.status === 'failed'" class="w-3 h-3 text-red-500" />
              <CheckCircle v-else class="w-3 h-3 text-green-500" />
              <span class="font-mono">
                {{ t('demo.retryComparison.attempt') }} {{ attempt.attempt }}
              </span>
              <span v-if="attempt.status === 'failed'" class="text-red-500">
                {{ t('demo.retryComparison.failed') }}
              </span>
              <span v-if="attempt.status === 'success'" class="text-green-500">
                {{ t('demo.retryComparison.success') }}
              </span>
            </div>

            <div
              v-if="query500.error.value && !query500.isFetching.value"
              class="text-xs text-red-500 pt-2 border-t mt-2"
            >
              {{ getErrorMessage(query500.error.value) }}
            </div>
          </div>
        </div>

        <!-- 404 Error Panel -->
        <div class="flex-1 space-y-3">
          <div class="flex items-center justify-between">
            <h4 class="font-medium text-sm">{{ t('demo.retryComparison.notFound') }}</h4>
            <Badge variant="secondary" class="text-xs">
              {{ t('demo.retryComparison.noRetry') }}
            </Badge>
          </div>

          <div class="text-xs text-muted-foreground space-y-1">
            <div>
              <span class="font-mono">status:</span> 404
            </div>
            <div>
              <span class="font-mono">recoverable:</span> false
            </div>
          </div>

          <Button
            size="sm"
            variant="outline"
            :disabled="query404.isFetching.value"
            class="w-full active:scale-95 transition-transform"
            @click="trigger404"
          >
            <RefreshCw v-if="query404.isFetching.value" class="w-4 h-4 mr-2 animate-spin" />
            {{ t('demo.retryComparison.trigger') }}
          </Button>

          <!-- Timeline -->
          <div class="bg-muted/50 rounded-lg p-3 min-h-[140px] space-y-2">
            <div
              v-if="!active404 && attempts404.length === 0"
              class="text-xs text-muted-foreground text-center py-8"
            >
              {{ t('demo.retryComparison.clickToStart') }}
            </div>

            <div
              v-for="(attempt, idx) in attempts404"
              :key="idx"
              class="flex items-center gap-2 text-xs motion-preset-slide-right motion-duration-[0.2s]"
              :style="{ animationDelay: `${idx * 100}ms` }"
            >
              <RefreshCw v-if="attempt.status === 'pending'" class="w-3 h-3 text-blue-500 animate-spin" />
              <XCircle v-else-if="attempt.status === 'failed'" class="w-3 h-3 text-red-500" />
              <CheckCircle v-else class="w-3 h-3 text-green-500" />
              <span class="font-mono">
                {{ t('demo.retryComparison.attempt') }} {{ attempt.attempt }}
              </span>
              <span v-if="attempt.status === 'failed'" class="text-red-500">
                {{ t('demo.retryComparison.failed') }}
              </span>
              <span v-if="attempt.status === 'success'" class="text-green-500">
                {{ t('demo.retryComparison.success') }}
              </span>
            </div>

            <div
              v-if="query404.error.value && !query404.isFetching.value"
              class="text-xs text-red-500 pt-2 border-t mt-2"
            >
              {{ getErrorMessage(query404.error.value) }}
            </div>
          </div>
        </div>
      </div>

      <div class="text-xs text-muted-foreground bg-muted/50 rounded-lg p-3">
        <strong>{{ t('demo.retryComparison.note') }}:</strong> {{ t('demo.retryComparison.noteText') }}
      </div>
    </div>
  </DemoSection>
</template>
