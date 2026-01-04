'use client';

import { useMemo, useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { toast } from 'sonner';

import {
  useGetCounterDemoCounterGet,
  getCounterDemoCounterGetQueryKey,
  useIncrementCounterDemoCounterIncrementPost,
  useResetCounterDemoCounterResetPost,
  type CounterResponse,
} from '@/src/gen';
import { useCounterId } from '@/hooks/useCounterId';
import { DemoSection } from './DemoSection';
import { Button } from '@/components/ui/button';

export function OptimisticDemo() {
  const t = useTranslations('demo.optimistic');
  const queryClient = useQueryClient();
  const counterId = useCounterId();

  // Track the last confirmed server value (updates only after server response)
  const [confirmedServerValue, setConfirmedServerValue] = useState<number | null>(null);

  const queryKey = useMemo(
    () => getCounterDemoCounterGetQueryKey({ counter_id: counterId }),
    [counterId],
  );

  const { data } = useGetCounterDemoCounterGet({ counter_id: counterId });

  const { mutate: increment, isPending: isIncrementing } =
    useIncrementCounterDemoCounterIncrementPost({
      mutation: {
        // Via the Cache approach: update cache directly for instant UI
        onMutate: async (variables) => {
          // Cancel outgoing refetches to prevent race conditions
          await queryClient.cancelQueries({ queryKey });

          // Snapshot current value for rollback
          const previousData = queryClient.getQueryData<CounterResponse>(queryKey);

          // Optimistically update cache
          const params = variables.params as { amount?: number } | undefined;
          const amount = params?.amount ?? 1;
          queryClient.setQueryData<CounterResponse>(
            queryKey,
            (old: CounterResponse | undefined) =>
              old ? { ...old, value: old.value + amount } : undefined
          );

          return { previousData };
        },
        onError: (_err, _variables, context: { previousData?: CounterResponse } | undefined) => {
          // Rollback to previous value on error
          if (context?.previousData) {
            queryClient.setQueryData<CounterResponse>(queryKey, context.previousData);
          }
          toast.error(t('error'));
        },
        onSuccess: (responseData) => {
          // Update confirmed server value only after successful server response
          setConfirmedServerValue(responseData.value);
        },
        onSettled: () => {
          // Always refetch after mutation to ensure sync with server
          void queryClient.invalidateQueries({ queryKey });
        },
      },
    });

  const { mutate: reset } = useResetCounterDemoCounterResetPost({
    mutation: {
      onSuccess: (responseData) => {
        setConfirmedServerValue(responseData.value);
      },
      onSettled: () => {
        void queryClient.invalidateQueries({ queryKey });
      },
    },
  });

  // Initialize confirmed value from initial data load
  useEffect(() => {
    if (data?.value !== undefined && confirmedServerValue === null) {
      setConfirmedServerValue(data.value);
    }
  }, [data?.value, confirmedServerValue]);

  const handleIncrement = (shouldFail: boolean) => {
    increment({ params: { counter_id: counterId, amount: 1, should_fail: shouldFail } });
  };

  return (
    <DemoSection icon="&#9889;" title={t('title')}>
      <div className="space-y-4">
        <div className="bg-muted rounded-lg p-4">
          <div className="text-center">
            {/* Counter value - pop animation on pending state */}
            <p
              className={`text-4xl font-bold mb-1 transition-transform duration-150 ${
                isIncrementing ? 'motion-preset-pop motion-duration-[0.15s]' : ''
              }`}
              key={isIncrementing ? 'pending' : data?.value}
            >
              {data?.value ?? '...'}
            </p>
            {isIncrementing && (
              <p className="text-xs text-yellow-500 motion-preset-slide-up-sm motion-preset-fade motion-duration-[0.2s]">
                {t('optimistic')}
              </p>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              {t('serverValue')}: {confirmedServerValue ?? '...'}
            </p>
          </div>
        </div>

        {/* Buttons with press feedback (#9) */}
        <div className="flex gap-2 flex-wrap">
          <Button
            disabled={isIncrementing}
            className="active:scale-95 hover:-translate-y-0.5 hover:shadow-md hover:shadow-primary/20 transition-all duration-150"
            onClick={() => { handleIncrement(false); }}
          >
            +1
          </Button>
          <Button
            variant="destructive"
            disabled={isIncrementing}
            className="active:scale-95 hover:-translate-y-0.5 hover:shadow-md transition-all duration-150"
            onClick={() => { handleIncrement(true); }}
          >
            +1 ({t('willFail')})
          </Button>
          <Button
            variant="outline"
            className="active:scale-95 hover:-translate-y-0.5 hover:shadow-md transition-all duration-150"
            onClick={() => { reset({ params: { counter_id: counterId } }); }}
          >
            {t('reset')}
          </Button>
        </div>

        <p className="text-xs text-muted-foreground">{t('note')}</p>
      </div>
    </DemoSection>
  );
}
