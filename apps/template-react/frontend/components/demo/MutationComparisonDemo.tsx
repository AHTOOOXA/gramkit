'use client';

import { useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import {
  useGetCounterDemoCounterGet,
  getCounterDemoCounterGetQueryKey,
  useIncrementCounterDemoCounterIncrementPost,
  useResetCounterDemoCounterResetPost,
  type CounterResponse,
} from '@/src/gen';
import { DemoSection } from './DemoSection';
import { Button } from '@/components/ui/button';

export function MutationComparisonDemo() {
  const t = useTranslations('demo.mutationComparison');
  const queryClient = useQueryClient();

  // Two separate counters for comparison
  const standardCounterId = 'standard-mutation-demo';
  const optimisticCounterId = 'optimistic-mutation-demo';

  const standardQueryKey = useMemo(
    () => getCounterDemoCounterGetQueryKey({ counter_id: standardCounterId }),
    []
  );
  const optimisticQueryKey = useMemo(
    () => getCounterDemoCounterGetQueryKey({ counter_id: optimisticCounterId }),
    []
  );

  // Standard counter query
  const { data: standardData, isFetching: standardFetching } =
    useGetCounterDemoCounterGet({ counter_id: standardCounterId });

  // Optimistic counter query
  const { data: optimisticData } =
    useGetCounterDemoCounterGet({ counter_id: optimisticCounterId });

  // Standard mutation (waits for server response)
  const { mutate: standardIncrement, isPending: standardPending } =
    useIncrementCounterDemoCounterIncrementPost({
      mutation: {
        onSettled: () => {
          void queryClient.invalidateQueries({ queryKey: standardQueryKey });
        },
      },
    });

  // Optimistic mutation (instant UI update)
  const { mutate: optimisticIncrement, isPending: optimisticPending } =
    useIncrementCounterDemoCounterIncrementPost({
      mutation: {
        onMutate: async (variables) => {
          await queryClient.cancelQueries({ queryKey: optimisticQueryKey });
          const previousData =
            queryClient.getQueryData<CounterResponse>(optimisticQueryKey);

          const params = variables.params as { amount?: number } | undefined;
          const amount = params?.amount ?? 1;
          queryClient.setQueryData<CounterResponse>(
            optimisticQueryKey,
            (old: CounterResponse | undefined) =>
              old ? { ...old, value: old.value + amount } : undefined
          );

          return { previousData };
        },
        onError: (
          _err,
          _variables,
          context: { previousData?: CounterResponse } | undefined
        ) => {
          if (context?.previousData) {
            queryClient.setQueryData<CounterResponse>(
              optimisticQueryKey,
              context.previousData
            );
          }
        },
        onSettled: () => {
          void queryClient.invalidateQueries({ queryKey: optimisticQueryKey });
        },
      },
    });

  // Reset mutations
  const { mutate: resetStandard } = useResetCounterDemoCounterResetPost({
    mutation: {
      onSettled: () => {
        void queryClient.invalidateQueries({ queryKey: standardQueryKey });
      },
    },
  });

  const { mutate: resetOptimistic } = useResetCounterDemoCounterResetPost({
    mutation: {
      onSettled: () => {
        void queryClient.invalidateQueries({ queryKey: optimisticQueryKey });
      },
    },
  });

  const handleReset = () => {
    resetStandard({ params: { counter_id: standardCounterId } });
    resetOptimistic({ params: { counter_id: optimisticCounterId } });
  };

  return (
    <DemoSection icon="&#9878;" title={t('title')}>
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">{t('description')}</p>

        <div className="grid grid-cols-2 gap-4">
          {/* Standard Mutation */}
          <div className="bg-muted rounded-lg p-4">
            <p className="text-xs font-medium text-muted-foreground mb-2">
              {t('standardMutation')}
            </p>
            <p
              className={`text-3xl font-bold text-center mb-3 transition-opacity duration-150 motion-preset-fade motion-duration-[0.2s] ${
                standardPending || standardFetching ? 'opacity-50' : 'opacity-100'
              }`}
              key={standardData?.value}
            >
              {standardData?.value ?? 0}
            </p>
            <Button
              size="sm"
              className="w-full active:scale-95 hover:-translate-y-0.5 hover:shadow-md hover:shadow-primary/20 transition-all duration-150"
              disabled={standardPending}
              onClick={() =>
                { standardIncrement({
                  params: { counter_id: standardCounterId, amount: 1 },
                }); }
              }
            >
              {standardPending ? t('waiting') : '+1'}
            </Button>
            <p className="text-xs text-center text-muted-foreground mt-2">
              {t('standardNote')}
            </p>
          </div>

          {/* Optimistic Mutation */}
          <div className="bg-muted rounded-lg p-4 border-2 border-primary/20 hover:border-primary/40 transition-colors duration-200">
            <p className="text-xs font-medium text-primary mb-2">
              {t('optimisticMutation')}
            </p>
            <p
              className={`text-3xl font-bold text-center mb-3 ${
                optimisticPending ? 'motion-preset-pop motion-duration-[0.15s]' : ''
              }`}
              key={optimisticData?.value}
            >
              {optimisticData?.value ?? 0}
            </p>
            <Button
              size="sm"
              variant="default"
              className="w-full active:scale-95 hover:-translate-y-0.5 hover:shadow-md hover:shadow-primary/20 transition-all duration-150"
              disabled={optimisticPending}
              onClick={() =>
                { optimisticIncrement({
                  params: { counter_id: optimisticCounterId, amount: 1 },
                }); }
              }
            >
              +1
            </Button>
            <p className="text-xs text-center text-muted-foreground mt-2">
              {t('optimisticNote')}
            </p>
          </div>
        </div>

        <Button
          variant="outline"
          size="sm"
          className="w-full active:scale-95 hover:-translate-y-0.5 hover:shadow-md transition-all duration-150"
          onClick={handleReset}
        >
          {t('resetBoth')}
        </Button>

        <p className="text-xs text-muted-foreground">{t('note')}</p>
      </div>
    </DemoSection>
  );
}
