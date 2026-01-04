'use client';

import { useState, useEffect, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import {
  useGetCounterDemoCounterGet,
  getCounterDemoCounterGetQueryKey,
} from '@/src/gen/hooks';
import { useCounterId } from '@/hooks/useCounterId';
import { DemoSection } from './DemoSection';
import { Button } from '@/components/ui/button';

export function CacheDemo() {
  const t = useTranslations('demo.cache');
  const queryClient = useQueryClient();
  const [now, setNow] = useState(Date.now());
  const counterId = useCounterId();

  const { data, dataUpdatedAt, isStale, isFetching, refetch } =
    useGetCounterDemoCounterGet(
      { counter_id: counterId },
      { query: { staleTime: 10 * 1000 } },
    );

  const timeSinceUpdate = useMemo(() => {
    if (!dataUpdatedAt) return '-';
    const seconds = Math.floor((now - dataUpdatedAt) / 1000);
    return `${String(seconds)}s`;
  }, [now, dataUpdatedAt]);

  const invalidateCache = () => {
    void queryClient.invalidateQueries({
      queryKey: getCounterDemoCounterGetQueryKey({ counter_id: counterId }),
    });
  };

  useEffect(() => {
    const intervalId = setInterval(() => {
      setNow(Date.now());
    }, 1000);

    return () => { clearInterval(intervalId); };
  }, []);

  return (
    <DemoSection icon="&#9202;" title={t('title')}>
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <span className="font-mono">isStale:</span>{' '}
            <span className={isStale ? 'text-yellow-500' : 'text-green-500'}>
              {String(isStale)}
            </span>
          </div>
          <div>
            <span className="font-mono">isFetching:</span>{' '}
            <span
              className={isFetching ? 'text-blue-500' : 'text-muted-foreground'}
            >
              {String(isFetching)}
            </span>
          </div>
        </div>

        <div className="bg-muted rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p
                className="text-2xl font-bold motion-preset-pop motion-duration-[0.2s]"
                key={data?.value}
              >
                {data?.value ?? '...'}
              </p>
              <p className="text-xs text-muted-foreground">
                {t('fetchedAgo')}: {timeSinceUpdate}
              </p>
            </div>
            <div className="text-right">
              <span
                className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs transition-all duration-300 ${
                  isStale
                    ? 'bg-yellow-500/20 text-yellow-500 motion-preset-pulse motion-duration-[2s] motion-loop-infinite'
                    : 'bg-green-500/20 text-green-500'
                }`}
              >
                {isStale && <span className="w-1.5 h-1.5 bg-yellow-500 rounded-full" />}
                {isStale ? t('stale') : t('fresh')}
              </span>
            </div>
          </div>
        </div>

        <div className="flex gap-2">
          <Button
            disabled={isFetching}
            onClick={() => refetch()}
            className="active:scale-95 hover:-translate-y-0.5 hover:shadow-md hover:shadow-primary/20 transition-all duration-150"
          >
            {t('refetch')}
          </Button>
          <Button
            variant="outline"
            onClick={invalidateCache}
            className="active:scale-95 hover:-translate-y-0.5 hover:shadow-md transition-all duration-150"
          >
            {t('invalidate')}
          </Button>
        </div>

        <p className="text-xs text-muted-foreground">{t('staleTimeNote')}</p>
      </div>
    </DemoSection>
  );
}
