<script setup lang="ts">
import { computed } from 'vue'
import { useQueries } from '@tanstack/vue-query'
import { useI18n } from 'vue-i18n'
import { Cloud, TrendingUp, Newspaper, RefreshCw } from 'lucide-vue-next'

import {
  getWeatherDemoWeatherGetQueryOptions,
  getStockDemoStockGetQueryOptions,
  getNewsDemoNewsGetQueryOptions,
} from '@/gen/hooks'
import DemoSection from './DemoSection.vue'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

const { t } = useI18n()

const results = useQueries({
  queries: [
    {
      ...getWeatherDemoWeatherGetQueryOptions({ city: 'Moscow', delay_ms: 800 }),
      staleTime: 30000,
    },
    {
      ...getStockDemoStockGetQueryOptions({ symbol: 'DEMO', delay_ms: 600 }),
      staleTime: 30000,
    },
    {
      ...getNewsDemoNewsGetQueryOptions({ delay_ms: 700 }),
      staleTime: 30000,
    },
  ],
})

const weatherQuery = computed(() => results.value[0])
const stockQuery = computed(() => results.value[1])
const newsQuery = computed(() => results.value[2])

const isAnyFetching = computed(() => results.value.some((r) => r.isFetching))
const loadedCount = computed(() => results.value.filter((r) => r.data).length)

const refetchAll = () => {
  results.value.forEach((r) => r.refetch())
}
</script>

<template>
  <DemoSection icon="&#9881;" :title="t('demo.parallel.title')">
    <div class="space-y-4">
      <div class="flex items-center gap-4 text-sm">
        <span>
          <span class="font-mono">loaded:</span>
          {{ loadedCount }}/3
        </span>
        <span>
          <span class="font-mono">fetching:</span>
          <span :class="isAnyFetching ? 'text-blue-500' : 'text-muted-foreground'">
            {{ String(isAnyFetching) }}
          </span>
        </span>
      </div>

      <div class="grid gap-3">
        <!-- Weather Card -->
        <div class="bg-muted rounded-lg p-3">
          <div class="flex items-center gap-2 mb-2">
            <Cloud class="w-4 h-4 text-blue-500" />
            <span class="text-sm font-medium">{{ t('demo.parallel.weather') }}</span>
            <span v-if="weatherQuery?.isFetching" class="text-xs text-blue-500 ml-auto">
              {{ t('demo.parallel.loading') }}
            </span>
          </div>
          <Skeleton v-if="weatherQuery?.isLoading" class="h-8 w-full" />
          <div
            v-else-if="weatherQuery?.data"
            class="flex items-baseline gap-2 motion-preset-fade motion-duration-[0.2s]"
          >
            <span class="text-2xl font-bold">{{ weatherQuery.data.temperature }}°C</span>
            <span class="text-muted-foreground">{{ weatherQuery.data.condition }}</span>
            <span class="text-xs text-muted-foreground ml-auto">
              {{ weatherQuery.data.city }}
            </span>
          </div>
        </div>

        <!-- Stock Card -->
        <div class="bg-muted rounded-lg p-3">
          <div class="flex items-center gap-2 mb-2">
            <TrendingUp class="w-4 h-4 text-green-500" />
            <span class="text-sm font-medium">{{ t('demo.parallel.stock') }}</span>
            <span v-if="stockQuery?.isFetching" class="text-xs text-blue-500 ml-auto">
              {{ t('demo.parallel.loading') }}
            </span>
          </div>
          <Skeleton v-if="stockQuery?.isLoading" class="h-8 w-full" />
          <div
            v-else-if="stockQuery?.data"
            class="flex items-baseline gap-2 motion-preset-fade motion-duration-[0.2s]"
          >
            <span class="text-2xl font-bold">${{ stockQuery.data.price }}</span>
            <span :class="stockQuery.data.change >= 0 ? 'text-green-500' : 'text-red-500'">
              {{ stockQuery.data.change >= 0 ? '+' : '' }}{{ stockQuery.data.change }}%
            </span>
            <span class="text-xs text-muted-foreground ml-auto">
              {{ stockQuery.data.symbol }}
            </span>
          </div>
        </div>

        <!-- News Card -->
        <div class="bg-muted rounded-lg p-3">
          <div class="flex items-center gap-2 mb-2">
            <Newspaper class="w-4 h-4 text-orange-500" />
            <span class="text-sm font-medium">{{ t('demo.parallel.news') }}</span>
            <span v-if="newsQuery?.isFetching" class="text-xs text-blue-500 ml-auto">
              {{ t('demo.parallel.loading') }}
            </span>
          </div>
          <Skeleton v-if="newsQuery?.isLoading" class="h-8 w-full" />
          <div v-else-if="newsQuery?.data" class="motion-preset-fade motion-duration-[0.2s]">
            <p class="text-sm font-medium line-clamp-1">
              {{ newsQuery.data.headline }}
            </p>
            <p class="text-xs text-muted-foreground">{{ newsQuery.data.source }}</p>
          </div>
        </div>
      </div>

      <Button
        variant="outline"
        :disabled="isAnyFetching"
        class="w-full active:scale-[0.98] transition-transform duration-100"
        @click="refetchAll"
      >
        <RefreshCw class="w-4 h-4 mr-2" :class="isAnyFetching ? 'animate-spin' : ''" />
        {{ t('demo.parallel.refetchAll') }}
      </Button>

      <p class="text-xs text-muted-foreground">{{ t('demo.parallel.note') }}</p>
    </div>
  </DemoSection>
</template>
