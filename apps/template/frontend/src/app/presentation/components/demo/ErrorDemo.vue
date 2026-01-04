<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { isApiError, getErrorMessage } from '@core/errors'
import { useUnreliableEndpointDemoUnreliableGet } from '@/gen/hooks'
import DemoSection from './DemoSection.vue'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'

const { t } = useI18n()
const hasTriggered = ref(false)

const { data, error, isFetching, refetch, failureCount } = useUnreliableEndpointDemoUnreliableGet(
  { fail_rate: 0.7 },
  {
    query: {
      enabled: () => hasTriggered.value,
      retry: 3,
      retryDelay: (attempt: number) => Math.min(1000 * 2 ** attempt, 5000),
    },
  }
)

// Only show loading when actually fetching (not when query is just disabled)
const isLoading = computed(() => hasTriggered.value && isFetching.value)

// Extract ApiError properties if available
const apiError = computed(() => (isApiError(error.value) ? error.value : null))

const triggerRequest = () => {
  hasTriggered.value = true
  refetch()
}
</script>

<template>
  <DemoSection icon="&#10060;" :title="t('demo.error.title')">
    <div class="space-y-4">
      <div class="flex items-center gap-4 text-sm flex-wrap">
        <span>
          <span class="font-mono">isError:</span>
          <span :class="error ? 'text-red-500' : 'text-green-500'">
            {{ !!error }}
          </span>
        </span>
        <span>
          <span class="font-mono">retries:</span>
          <span>{{ failureCount }}/3</span>
        </span>
        <span v-if="apiError">
          <span class="font-mono">willRetry:</span>
          <span :class="apiError.recoverable ? 'text-yellow-500' : 'text-red-500'">
            {{ apiError.recoverable ? 'yes' : 'no' }}
          </span>
        </span>
      </div>

      <div class="bg-muted rounded-lg p-4 min-h-[80px]">
        <template v-if="isLoading">
          <!-- Loading pulse (#10) -->
          <p class="text-muted-foreground motion-preset-pulse motion-duration-[1.5s] motion-loop-infinite">
            {{ t('demo.error.trying') }}...
          </p>
        </template>
        <template v-else-if="error">
          <div class="space-y-3">
            <!-- Error shake (#8) -->
            <Alert variant="destructive" class="motion-preset-shake motion-duration-[0.4s]">
              <AlertDescription class="flex items-center justify-between">
                <span>{{ getErrorMessage(error) }}</span>
                <Button
                  size="sm"
                  variant="outline"
                  class="active:scale-95 hover:-translate-y-0.5 hover:shadow-md transition-all duration-150"
                  @click="refetch"
                >
                  {{ t('demo.error.retry') }}
                </Button>
              </AlertDescription>
            </Alert>

            <!-- ApiError properties display -->
            <div v-if="apiError" class="bg-background/50 rounded-md p-3 text-xs font-mono space-y-1 border">
              <div class="text-muted-foreground mb-2 font-sans text-xs font-medium">
                ApiError Properties:
              </div>
              <div class="flex items-center gap-2">
                <span class="text-muted-foreground">message:</span>
                <span class="text-foreground">"{{ apiError.message }}"</span>
              </div>
              <div class="flex items-center gap-2">
                <span class="text-muted-foreground">recoverable:</span>
                <Badge :variant="apiError.recoverable ? 'default' : 'secondary'" class="text-xs h-5">
                  {{ String(apiError.recoverable) }}
                </Badge>
              </div>
              <div class="flex items-center gap-2">
                <span class="text-muted-foreground">status:</span>
                <span class="text-foreground">{{ apiError.status }}</span>
              </div>
            </div>
          </div>
        </template>
        <template v-else-if="data">
          <!-- Success pop (#7) -->
          <p class="text-green-500 font-medium motion-preset-pop motion-duration-[0.3s]">
            {{ data.message }}
          </p>
        </template>
        <template v-else>
          <p class="text-muted-foreground">{{ t('demo.error.clickToTest') }}</p>
        </template>
      </div>

      <!-- Button with press feedback (#9) -->
      <Button
        :disabled="isLoading"
        class="active:scale-95 transition-transform duration-100"
        @click="triggerRequest"
      >
        {{ t('demo.error.trigger') }} (70% {{ t('demo.error.failRate') }})
      </Button>
    </div>
  </DemoSection>
</template>
