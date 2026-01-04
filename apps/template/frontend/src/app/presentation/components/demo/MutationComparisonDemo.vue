<script setup lang="ts">
import { useQueryClient } from '@tanstack/vue-query'
import { useI18n } from 'vue-i18n'

import {
  useGetCounterDemoCounterGet,
  getCounterDemoCounterGetQueryKey,
  useIncrementCounterDemoCounterIncrementPost,
  useResetCounterDemoCounterResetPost,
  type CounterResponse,
} from '@/gen'
import DemoSection from './DemoSection.vue'
import { Button } from '@/components/ui/button'

const { t } = useI18n()
const queryClient = useQueryClient()

const standardCounterId = 'standard-mutation-demo'
const optimisticCounterId = 'optimistic-mutation-demo'

const standardQueryKey = getCounterDemoCounterGetQueryKey({ counter_id: standardCounterId })
const optimisticQueryKey = getCounterDemoCounterGetQueryKey({ counter_id: optimisticCounterId })

// Standard counter query
const { data: standardData, isFetching: standardFetching } = useGetCounterDemoCounterGet({
  counter_id: standardCounterId,
})

// Optimistic counter query
const { data: optimisticData } = useGetCounterDemoCounterGet({
  counter_id: optimisticCounterId,
})

// Standard mutation (waits for server response)
const { mutate: standardIncrement, isPending: standardPending } =
  useIncrementCounterDemoCounterIncrementPost({
    mutation: {
      onSettled: () => {
        queryClient.invalidateQueries({ queryKey: standardQueryKey })
      },
    },
  })

// Optimistic mutation (instant UI update)
const { mutate: optimisticIncrement, isPending: optimisticPending } =
  useIncrementCounterDemoCounterIncrementPost({
    mutation: {
      onMutate: async (variables) => {
        await queryClient.cancelQueries({ queryKey: optimisticQueryKey })
        const previousData = queryClient.getQueryData<CounterResponse>(optimisticQueryKey)

        const params = variables.params as { amount?: number } | undefined
        const amount = params?.amount ?? 1
        queryClient.setQueryData<CounterResponse>(optimisticQueryKey, (old) =>
          old ? { ...old, value: old.value + amount } : undefined
        )

        return { previousData }
      },
      onError: (_err, _variables, context) => {
        if (context?.previousData) {
          queryClient.setQueryData<CounterResponse>(optimisticQueryKey, context.previousData)
        }
      },
      onSettled: () => {
        queryClient.invalidateQueries({ queryKey: optimisticQueryKey })
      },
    },
  })

// Reset mutations
const { mutate: resetStandard } = useResetCounterDemoCounterResetPost({
  mutation: {
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: standardQueryKey })
    },
  },
})

const { mutate: resetOptimistic } = useResetCounterDemoCounterResetPost({
  mutation: {
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: optimisticQueryKey })
    },
  },
})

const handleReset = () => {
  resetStandard({ params: { counter_id: standardCounterId } })
  resetOptimistic({ params: { counter_id: optimisticCounterId } })
}
</script>

<template>
  <DemoSection icon="&#9878;" :title="t('demo.mutationComparison.title')">
    <div class="space-y-4">
      <p class="text-sm text-muted-foreground">{{ t('demo.mutationComparison.description') }}</p>

      <div class="grid grid-cols-2 gap-4">
        <!-- Standard Mutation -->
        <div class="bg-muted rounded-lg p-4">
          <p class="text-xs font-medium text-muted-foreground mb-2">
            {{ t('demo.mutationComparison.standardMutation') }}
          </p>
          <p
            class="text-3xl font-bold text-center mb-3 transition-opacity duration-150"
            :class="standardPending || standardFetching ? 'opacity-50' : 'opacity-100'"
          >
            {{ standardData?.value ?? 0 }}
          </p>
          <Button
            size="sm"
            class="w-full active:scale-95 transition-transform duration-100"
            :disabled="standardPending"
            @click="
              standardIncrement({
                params: { counter_id: standardCounterId, amount: 1 },
              })
            "
          >
            {{ standardPending ? t('demo.mutationComparison.waiting') : '+1' }}
          </Button>
          <p class="text-xs text-center text-muted-foreground mt-2">
            {{ t('demo.mutationComparison.standardNote') }}
          </p>
        </div>

        <!-- Optimistic Mutation -->
        <div class="bg-muted rounded-lg p-4 border-2 border-primary/20">
          <p class="text-xs font-medium text-primary mb-2">
            {{ t('demo.mutationComparison.optimisticMutation') }}
          </p>
          <p
            class="text-3xl font-bold text-center mb-3 transition-transform duration-150"
            :class="optimisticPending ? 'scale-110' : 'scale-100'"
          >
            {{ optimisticData?.value ?? 0 }}
          </p>
          <Button
            size="sm"
            variant="default"
            class="w-full active:scale-95 transition-transform duration-100"
            :disabled="optimisticPending"
            @click="
              optimisticIncrement({
                params: { counter_id: optimisticCounterId, amount: 1 },
              })
            "
          >
            +1
          </Button>
          <p class="text-xs text-center text-muted-foreground mt-2">
            {{ t('demo.mutationComparison.optimisticNote') }}
          </p>
        </div>
      </div>

      <Button variant="outline" size="sm" class="w-full" @click="handleReset">
        {{ t('demo.mutationComparison.resetBoth') }}
      </Button>

      <p class="text-xs text-muted-foreground">{{ t('demo.mutationComparison.note') }}</p>
    </div>
  </DemoSection>
</template>
