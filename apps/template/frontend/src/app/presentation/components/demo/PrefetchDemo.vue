<script setup lang="ts">
import { ref } from 'vue'
import { useQueryClient } from '@tanstack/vue-query'
import { useI18n } from 'vue-i18n'

import {
  useGetItemDetailDemoItemsItemIdGet,
  getItemDetailDemoItemsItemIdGetQueryOptions,
} from '@/gen/hooks'
import DemoSection from './DemoSection.vue'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

const ITEMS = [
  { id: 1, label: 'Item 1' },
  { id: 2, label: 'Item 2' },
  { id: 3, label: 'Item 3' },
]

const { t } = useI18n()
const queryClient = useQueryClient()
const selectedId = ref<number | null>(null)
const prefetchedIds = ref<Set<number>>(new Set())

const { data, isFetching } = useGetItemDetailDemoItemsItemIdGet(
  () => selectedId.value ?? 0,
  { delay_ms: 800 },
  { query: { enabled: () => selectedId.value !== null } }
)

const handlePrefetch = async (itemId: number) => {
  if (prefetchedIds.value.has(itemId)) return

  await queryClient.prefetchQuery(
    getItemDetailDemoItemsItemIdGetQueryOptions(itemId, { delay_ms: 800 })
  )
  prefetchedIds.value = new Set(prefetchedIds.value).add(itemId)
}

const handleSelect = (itemId: number) => {
  selectedId.value = itemId
}
</script>

<template>
  <DemoSection icon="&#128640;" :title="t('demo.prefetch.title')">
    <div class="space-y-4">
      <p class="text-sm text-muted-foreground">{{ t('demo.prefetch.description') }}</p>

      <div class="flex gap-2">
        <Button
          v-for="item in ITEMS"
          :key="item.id"
          :variant="selectedId === item.id ? 'default' : 'outline'"
          size="sm"
          class="relative active:scale-95 transition-transform duration-100"
          @mouseenter="handlePrefetch(item.id)"
          @click="handleSelect(item.id)"
        >
          {{ item.label }}
          <span
            v-if="prefetchedIds.has(item.id) && selectedId !== item.id"
            class="absolute -top-1 -right-1 w-2 h-2 bg-green-500 rounded-full motion-preset-pop"
          />
        </Button>
      </div>

      <div class="bg-muted rounded-lg p-4 min-h-[100px]">
        <p v-if="selectedId === null" class="text-muted-foreground text-center">
          {{ t('demo.prefetch.hoverHint') }}
        </p>
        <template v-else-if="isFetching">
          <Skeleton class="h-5 w-1/2 mb-2" />
          <Skeleton class="h-4 w-3/4 mb-2" />
          <Skeleton class="h-4 w-full" />
        </template>
        <div v-else-if="data" class="motion-preset-fade motion-duration-[0.2s]">
          <p class="font-semibold text-lg">{{ data.title }}</p>
          <p class="text-sm text-muted-foreground mt-1">{{ data.description }}</p>
          <p class="text-sm mt-2">{{ data.details }}</p>
          <p class="text-xs text-muted-foreground mt-2">
            {{ t('demo.prefetch.fetchedAt') }}: {{ data.fetched_at }}
          </p>
        </div>
      </div>

      <div class="flex items-center gap-2 text-xs text-muted-foreground">
        <span class="w-2 h-2 bg-green-500 rounded-full" />
        <span>{{ t('demo.prefetch.prefetchedIndicator') }}</span>
      </div>

      <p class="text-xs text-muted-foreground">{{ t('demo.prefetch.note') }}</p>
    </div>
  </DemoSection>
</template>
