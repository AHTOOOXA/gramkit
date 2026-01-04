<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSlowEndpointDemoSlowGet } from '@/gen/hooks'
import DemoSection from './DemoSection.vue'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

const { t } = useI18n()
const hasTriggered = ref(false)

const { data, isFetching, refetch } = useSlowEndpointDemoSlowGet(
  { delay_ms: 2000 },
  { query: { enabled: () => hasTriggered.value } }
)

// Only show loading when actually fetching (not when query is just disabled)
const isLoading = computed(() => hasTriggered.value && isFetching.value)

const triggerLoad = () => {
  hasTriggered.value = true
  refetch()
}
</script>

<template>
  <DemoSection icon="&#9203;" :title="t('demo.loading.title')">
    <div class="space-y-4">
      <div class="flex items-center gap-2 text-sm">
        <span class="font-mono">isFetching:</span>
        <span
:class="isLoading
          ? 'text-yellow-500 motion-preset-pulse motion-duration-[1s] motion-loop-infinite'
          : 'text-green-500'">
          {{ isLoading }}
        </span>
      </div>

      <div class="bg-muted rounded-lg p-4 min-h-[80px]">
        <template v-if="isLoading">
          <Skeleton class="h-4 w-3/4 mb-2" />
          <Skeleton class="h-4 w-1/2" />
        </template>
        <div v-else-if="data" class="motion-preset-fade motion-preset-slide-up-sm motion-duration-[0.3s]">
          <p class="font-medium">{{ data.message }}</p>
          <p class="text-xs text-muted-foreground mt-1">
            {{ t('demo.loading.loadedAt') }}: {{ data.timestamp }}
          </p>
        </div>
        <template v-else>
          <p class="text-muted-foreground">{{ t('demo.loading.clickToLoad') }}</p>
        </template>
      </div>

      <div class="flex gap-2">
        <Button :disabled="isLoading" class="active:scale-95 hover:-translate-y-0.5 hover:shadow-md hover:shadow-primary/20 transition-all duration-150" @click="triggerLoad">
          {{ isLoading ? t('demo.loading.loading') : t('demo.loading.trigger') }}
        </Button>
      </div>
    </div>
  </DemoSection>
</template>
