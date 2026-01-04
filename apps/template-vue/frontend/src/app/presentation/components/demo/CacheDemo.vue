<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useQueryClient } from '@tanstack/vue-query'
import { useI18n } from 'vue-i18n'
import { useGetCounterDemoCounterGet, getCounterDemoCounterGetQueryKey } from '@/gen/hooks'
import { useCounterId } from '@app/composables/useCounterId'
import DemoSection from './DemoSection.vue'
import { Button } from '@/components/ui/button'

const { t } = useI18n()
const queryClient = useQueryClient()
const now = ref(Date.now())
const counterId = useCounterId()

const { data, dataUpdatedAt, isStale, isFetching, refetch } = useGetCounterDemoCounterGet(
  { counter_id: counterId },
  { query: { staleTime: 10 * 1000 } },
)

const timeSinceUpdate = computed(() => {
  if (!dataUpdatedAt.value) return '-'
  const seconds = Math.floor((now.value - dataUpdatedAt.value) / 1000)
  return `${seconds}s`
})

const invalidateCache = () => {
  queryClient.invalidateQueries({ queryKey: getCounterDemoCounterGetQueryKey({ counter_id: counterId }) })
}

let intervalId: ReturnType<typeof setInterval> | null = null
onMounted(() => {
  intervalId = setInterval(() => {
    now.value = Date.now()
  }, 1000)
})
onUnmounted(() => {
  if (intervalId) clearInterval(intervalId)
})
</script>

<template>
  <DemoSection icon="&#9202;" :title="t('demo.cache.title')">
    <div class="space-y-4">
      <div class="grid grid-cols-2 gap-2 text-sm">
        <div>
          <span class="font-mono">isStale:</span>
          <span :class="isStale ? 'text-yellow-500' : 'text-green-500'">
            {{ isStale }}
          </span>
        </div>
        <div>
          <span class="font-mono">isFetching:</span>
          <span :class="isFetching ? 'text-blue-500' : 'text-muted-foreground'">
            {{ isFetching }}
          </span>
        </div>
      </div>

      <div class="bg-muted rounded-lg p-4">
        <div class="flex items-center justify-between">
          <div>
            <p :key="data?.value" class="text-2xl font-bold motion-preset-pop motion-duration-[0.2s]">{{ data?.value ?? '...' }}</p>
            <p class="text-xs text-muted-foreground">
              {{ t('demo.cache.fetchedAgo') }}: {{ timeSinceUpdate }}
            </p>
          </div>
          <div class="text-right">
            <span
              class="inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs transition-all duration-300"
              :class="isStale
                ? 'bg-yellow-500/20 text-yellow-500 motion-preset-pulse motion-duration-[2s] motion-loop-infinite'
                : 'bg-green-500/20 text-green-500'"
            >
              <span v-if="isStale" class="w-1.5 h-1.5 bg-yellow-500 rounded-full" />
              {{ isStale ? t('demo.cache.stale') : t('demo.cache.fresh') }}
            </span>
          </div>
        </div>
      </div>

      <div class="flex gap-2">
        <Button :disabled="isFetching" class="active:scale-95 hover:-translate-y-0.5 hover:shadow-md hover:shadow-primary/20 transition-all duration-150" @click="() => refetch()">
          {{ t('demo.cache.refetch') }}
        </Button>
        <Button variant="outline" class="active:scale-95 hover:-translate-y-0.5 hover:shadow-md transition-all duration-150" @click="invalidateCache">
          {{ t('demo.cache.invalidate') }}
        </Button>
      </div>

      <p class="text-xs text-muted-foreground">
        {{ t('demo.cache.staleTimeNote') }}
      </p>
    </div>
  </DemoSection>
</template>
