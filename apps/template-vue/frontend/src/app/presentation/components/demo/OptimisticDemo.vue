<script setup lang="ts">
import { useQueryClient } from '@tanstack/vue-query'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import {
  useGetCounterDemoCounterGet,
  getCounterDemoCounterGetQueryKey,
  useIncrementCounterDemoCounterIncrementPost,
  useResetCounterDemoCounterResetPost,
  type CounterResponse,
} from '@/gen'
import { useCounterId } from '@app/composables/useCounterId'
import DemoSection from './DemoSection.vue'
import { Button } from '@/components/ui/button'

const { t } = useI18n()
const queryClient = useQueryClient()
const counterId = useCounterId()

const queryKey = getCounterDemoCounterGetQueryKey({ counter_id: counterId })

const { data } = useGetCounterDemoCounterGet({ counter_id: counterId })

const { mutate: increment, isPending: isIncrementing } = useIncrementCounterDemoCounterIncrementPost({
  mutation: {
    // Via the Cache approach: update cache directly for instant UI
    onMutate: async (variables) => {
      // Cancel outgoing refetches to prevent race conditions
      await queryClient.cancelQueries({ queryKey })

      // Snapshot current value for rollback
      const previousData = queryClient.getQueryData<CounterResponse>(queryKey)

      // Optimistically update cache
      const params = variables.params as { amount?: number } | undefined
      const amount = params?.amount ?? 1
      queryClient.setQueryData<CounterResponse>(queryKey, (old: CounterResponse | undefined) =>
        old ? { ...old, value: old.value + amount } : undefined
      )

      return { previousData }
    },
    onError: (_err, _variables, context) => {
      // Rollback to previous value on error
      if (context?.previousData) {
        queryClient.setQueryData(queryKey, context.previousData)
      }
      toast.error(t('demo.optimistic.error'))
    },
    onSettled: () => {
      // Always refetch after mutation to ensure sync with server
      queryClient.invalidateQueries({ queryKey })
    },
  },
})

const { mutate: reset } = useResetCounterDemoCounterResetPost({
  mutation: {
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey })
    },
  },
})

const handleIncrement = (shouldFail: boolean) => {
  increment({ params: { counter_id: counterId, amount: 1, should_fail: shouldFail } })
}
</script>

<template>
  <DemoSection icon="&#9889;" :title="t('demo.optimistic.title')">
    <div class="space-y-4">
      <div class="bg-muted rounded-lg p-4">
        <div class="text-center">
          <!-- Counter value - scale animation on pending state -->
          <p
            class="text-4xl font-bold mb-1 transition-transform duration-150"
            :class="isIncrementing ? 'scale-105' : 'scale-100'"
          >
            {{ data?.value ?? '...' }}
          </p>
          <p
            v-if="isIncrementing"
            class="text-xs text-yellow-500 motion-preset-fade motion-duration-[0.2s]"
          >
            {{ t('demo.optimistic.optimistic') }}
          </p>
          <p class="text-xs text-muted-foreground mt-1">
            {{ t('demo.optimistic.serverValue') }}: {{ data?.value ?? '...' }}
          </p>
        </div>
      </div>

      <!-- Buttons with press feedback (#9) -->
      <div class="flex gap-2 flex-wrap">
        <Button
          :disabled="isIncrementing"
          class="active:scale-95 hover:-translate-y-0.5 hover:shadow-md hover:shadow-primary/20 transition-all duration-150"
          @click="handleIncrement(false)"
        >
          +1
        </Button>
        <Button
          variant="destructive"
          :disabled="isIncrementing"
          class="active:scale-95 hover:-translate-y-0.5 hover:shadow-md hover:shadow-primary/20 transition-all duration-150"
          @click="handleIncrement(true)"
        >
          +1 ({{ t('demo.optimistic.willFail') }})
        </Button>
        <Button
          variant="outline"
          class="active:scale-95 hover:-translate-y-0.5 hover:shadow-md hover:shadow-primary/20 transition-all duration-150"
          @click="reset({ params: { counter_id: counterId } })"
        >
          {{ t('demo.optimistic.reset') }}
        </Button>
      </div>

      <p class="text-xs text-muted-foreground">
        {{ t('demo.optimistic.note') }}
      </p>
    </div>
  </DemoSection>
</template>
