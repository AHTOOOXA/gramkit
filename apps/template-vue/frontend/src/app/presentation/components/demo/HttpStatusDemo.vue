<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMutation } from '@tanstack/vue-query'

import { isApiError, getErrorMessage } from '@core/errors'
import { triggerErrorDemoErrorStatusCodeGet } from '@/gen/client/triggerErrorDemoErrorStatusCodeGet'
import DemoSection from './DemoSection.vue'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'

const { t } = useI18n()

// HTTP status codes to demo
const STATUS_CODES = [
  { code: 400, label: '400', description: 'Bad Request' },
  { code: 401, label: '401', description: 'Unauthorized' },
  { code: 403, label: '403', description: 'Forbidden' },
  { code: 404, label: '404', description: 'Not Found' },
  { code: 409, label: '409', description: 'Conflict' },
  { code: 422, label: '422', description: 'Validation' },
  { code: 429, label: '429', description: 'Rate Limit' },
  { code: 500, label: '500', description: 'Server Error' },
  { code: 503, label: '503', description: 'Unavailable' },
] as const

interface ErrorInfo {
  statusCode: number
  message: string
  recoverable: boolean
  willRetry: boolean
}

const lastError = ref<ErrorInfo | null>(null)
const activeCode = ref<number | null>(null)

const mutation = useMutation({
  mutationFn: async (statusCode: number) => {
    activeCode.value = statusCode
    // Uses generated client - error gets classified by axios interceptor
    await triggerErrorDemoErrorStatusCodeGet(statusCode)
  },
  onError: (error) => {
    if (isApiError(error)) {
      lastError.value = {
        statusCode: error.status,
        message: error.message,
        recoverable: error.recoverable,
        willRetry: error.recoverable,
      }
    } else {
      lastError.value = {
        statusCode: activeCode.value ?? 0,
        message: getErrorMessage(error),
        recoverable: false,
        willRetry: false,
      }
    }
    activeCode.value = null
  },
})

const triggerError = (statusCode: number) => {
  lastError.value = null
  mutation.mutate(statusCode)
}

const getButtonVariant = (code: number) => {
  if (code >= 500) return 'destructive'
  if (code === 401 || code === 403) return 'secondary'
  return 'outline'
}
</script>

<template>
  <DemoSection icon="&#128679;" :title="t('demo.httpStatus.title')">
    <div class="space-y-4">
      <p class="text-sm text-muted-foreground">
        {{ t('demo.httpStatus.description') }}
      </p>

      <!-- Status code buttons -->
      <div class="flex flex-wrap gap-2">
        <Button
          v-for="{ code, label, description } in STATUS_CODES"
          :key="code"
          :variant="getButtonVariant(code)"
          size="sm"
          :disabled="mutation.isPending.value"
          class="text-xs active:scale-95 transition-transform"
          @click="triggerError(code)"
        >
          <span v-if="activeCode === code" class="animate-pulse">...</span>
          <template v-else>
            <span class="font-mono font-bold">{{ label }}</span>
            <span class="ml-1 opacity-70 hidden sm:inline">{{ description }}</span>
          </template>
        </Button>
      </div>

      <!-- Result display -->
      <div class="bg-muted rounded-lg p-4 min-h-[120px]">
        <div v-if="lastError" class="space-y-3 motion-preset-fade motion-duration-[0.3s]">
          <Alert variant="destructive">
            <AlertDescription class="font-mono text-sm">
              {{ lastError.message }}
            </AlertDescription>
          </Alert>

          <!-- Classification details -->
          <div class="bg-background/50 rounded-md p-3 text-xs font-mono space-y-2 border">
            <div class="text-muted-foreground mb-2 font-sans text-xs font-medium">
              Error Classification:
            </div>
            <div class="grid grid-cols-2 gap-2">
              <div class="flex items-center gap-2">
                <span class="text-muted-foreground">status:</span>
                <Badge variant="outline" class="text-xs h-5 font-mono">
                  {{ lastError.statusCode }}
                </Badge>
              </div>
              <div class="flex items-center gap-2">
                <span class="text-muted-foreground">recoverable:</span>
                <Badge :variant="lastError.recoverable ? 'default' : 'secondary'" class="text-xs h-5">
                  {{ String(lastError.recoverable) }}
                </Badge>
              </div>
            </div>
            <div class="flex items-center gap-2 pt-1 border-t">
              <span class="text-muted-foreground">TanStack Query:</span>
              <span :class="lastError.willRetry ? 'text-yellow-500' : 'text-muted-foreground'">
                {{ lastError.willRetry ? 'Will retry (server error)' : 'No retry (client error)' }}
              </span>
            </div>
          </div>
        </div>
        <div v-else class="flex items-center justify-center h-full text-muted-foreground text-sm">
          {{ t('demo.httpStatus.clickToTest') }}
        </div>
      </div>

      <!-- Legend -->
      <div class="text-xs text-muted-foreground space-y-1">
        <div class="flex items-center gap-2">
          <Badge variant="outline" class="text-xs">4xx</Badge>
          <span>{{ t('demo.httpStatus.clientErrors') }}</span>
        </div>
        <div class="flex items-center gap-2">
          <Badge variant="destructive" class="text-xs">5xx</Badge>
          <span>{{ t('demo.httpStatus.serverErrors') }}</span>
        </div>
      </div>
    </div>
  </DemoSection>
</template>
