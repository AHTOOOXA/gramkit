<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { useInfiniteQuery } from '@tanstack/vue-query'
import { useI18n } from 'vue-i18n'

import { getPaginatedItemsDemoItemsGet } from '@/gen/client'
import type { PaginatedResponse } from '@/gen/models'
import DemoSection from './DemoSection.vue'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

const { t } = useI18n()
const sentinelRef = ref<HTMLDivElement | null>(null)

const {
  data,
  fetchNextPage,
  hasNextPage,
  isFetchingNextPage,
  isLoading,
  isError,
  refetch,
} = useInfiniteQuery({
  queryKey: ['demo', 'infinite-items'],
  queryFn: async ({ pageParam }) => {
    return getPaginatedItemsDemoItemsGet({
      cursor: pageParam,
      limit: 5,
      delay_ms: 500,
    })
  },
  initialPageParam: 0,
  getNextPageParam: (lastPage: PaginatedResponse) => lastPage.next_cursor,
})

const allItems = computed(() => data.value?.pages.flatMap((page) => page.items) ?? [])
const total = computed(() => data.value?.pages[0]?.total ?? 0)

let observer: IntersectionObserver | null = null

// Watch for sentinel element availability (it's inside a conditional template)
watch(sentinelRef, (el) => {
  // Cleanup previous observer
  observer?.disconnect()

  if (!el) return

  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting && hasNextPage.value && !isFetchingNextPage.value) {
        fetchNextPage()
      }
    },
    { threshold: 0.1 }
  )

  observer.observe(el)
})

onUnmounted(() => {
  observer?.disconnect()
})
</script>

<template>
  <DemoSection icon="&#128214;" :title="t('demo.infiniteScroll.title')">
    <div class="space-y-4">
      <div class="flex items-center gap-4 text-sm">
        <span>
          <span class="font-mono">loaded:</span>
          {{ allItems.length }}/{{ total }}
        </span>
        <span>
          <span class="font-mono">hasMore:</span>
          <span :class="hasNextPage ? 'text-green-500' : 'text-muted-foreground'">
            {{ String(hasNextPage) }}
          </span>
        </span>
      </div>

      <div class="bg-muted rounded-lg p-3 max-h-[200px] overflow-y-auto space-y-2">
        <template v-if="isLoading">
          <Skeleton class="h-10 w-full rounded animate-pulse" />
          <Skeleton class="h-10 w-full rounded animate-pulse" />
          <Skeleton class="h-10 w-full rounded animate-pulse" />
        </template>
        <template v-else-if="isError">
          <div class="text-center py-4 motion-preset-shake motion-duration-[0.4s]">
            <p class="text-destructive mb-2">{{ t('demo.infiniteScroll.error') }}</p>
            <Button size="sm" variant="outline" class="active:scale-95 hover:-translate-y-0.5 hover:shadow-md transition-all duration-150" @click="refetch()">
              {{ t('demo.infiniteScroll.retry') }}
            </Button>
          </div>
        </template>
        <template v-else-if="allItems.length === 0">
          <p class="text-muted-foreground text-center py-4">{{ t('demo.infiniteScroll.empty') }}</p>
        </template>
        <template v-else>
          <div
            v-for="(item, index) in allItems"
            :key="item.id"
            class="bg-background rounded p-2 text-sm motion-preset-slide-up motion-duration-[0.2s]"
            :style="{ animationDelay: `${(index % 5) * 50}ms` }"
          >
            <span class="font-medium">{{ item.title }}</span>
            <span class="text-muted-foreground ml-2">- {{ item.description }}</span>
          </div>
          <!-- Sentinel element for intersection observer -->
          <div ref="sentinelRef" class="h-1" />
        </template>

        <div v-if="isFetchingNextPage" class="space-y-2">
          <Skeleton class="h-10 w-full rounded animate-pulse" />
          <Skeleton class="h-10 w-full rounded animate-pulse" />
        </div>
      </div>

      <p class="text-xs text-muted-foreground">{{ t('demo.infiniteScroll.note') }}</p>
    </div>
  </DemoSection>
</template>
