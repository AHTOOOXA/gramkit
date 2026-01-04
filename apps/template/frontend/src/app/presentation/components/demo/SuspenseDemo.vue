<script setup lang="ts">
import { ref, computed } from 'vue'
import { useQueryClient } from '@tanstack/vue-query'
import { useI18n } from 'vue-i18n'

import { useGetItemDetailDemoItemsItemIdGet } from '@/gen/hooks'
import DemoSection from './DemoSection.vue'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'

const { t } = useI18n()
const queryClient = useQueryClient()
const selectedId = ref(1)

const { data, isLoading, isError, refetch } = useGetItemDetailDemoItemsItemIdGet(
  () => selectedId.value,
  { delay_ms: 1000 },
)

const handleChangeItem = (newId: number) => {
  // Clear cache to force re-fetch and show loading state
  queryClient.removeQueries({
    queryKey: [{ url: '/demo/items/:item_id', params: { item_id: newId } }],
  })
  selectedId.value = newId
}

// Show loading state visually distinct from data state
const showSkeleton = computed(() => isLoading.value && !data.value)
</script>

<template>
  <DemoSection icon="&#9200;" :title="t('demo.suspense.title')">
    <div class="space-y-4">
      <p class="text-sm text-muted-foreground">{{ t('demo.suspense.description') }}</p>

      <div class="flex gap-2">
        <Button
          v-for="id in [1, 2, 3]"
          :key="id"
          :variant="selectedId === id ? 'default' : 'outline'"
          size="sm"
          class="active:scale-95 transition-transform duration-100"
          @click="handleChangeItem(id)"
        >
          Item {{ id }}
        </Button>
      </div>

      <div class="bg-muted rounded-lg p-4 min-h-[80px]">
        <Alert v-if="isError" variant="destructive">
          <AlertDescription class="flex items-center justify-between">
            <span>{{ t('demo.suspense.errorOccurred') }}</span>
            <Button size="sm" variant="outline" @click="refetch()">
              {{ t('demo.suspense.retry') }}
            </Button>
          </AlertDescription>
        </Alert>
        <template v-else-if="showSkeleton">
          <div class="space-y-2">
            <Skeleton class="h-5 w-1/2" />
            <Skeleton class="h-4 w-3/4" />
            <p class="text-xs text-blue-500 mt-2">{{ t('demo.suspense.suspenseLoading') }}</p>
          </div>
        </template>
        <div v-else-if="data" class="motion-preset-fade motion-duration-[0.3s]">
          <p class="font-semibold">{{ data.title }}</p>
          <p class="text-sm text-muted-foreground">{{ data.description }}</p>
        </div>
      </div>

      <div class="bg-card border rounded-lg p-3">
        <p class="text-xs font-medium mb-2">{{ t('demo.suspense.howItWorks') }}:</p>
        <ul class="text-xs text-muted-foreground space-y-1">
          <li>• {{ t('demo.suspense.point1') }}</li>
          <li>• {{ t('demo.suspense.point2') }}</li>
          <li>• {{ t('demo.suspense.point3') }}</li>
        </ul>
      </div>

      <p class="text-xs text-muted-foreground">{{ t('demo.suspense.note') }}</p>
    </div>
  </DemoSection>
</template>
