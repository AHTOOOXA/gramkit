'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { useSlowEndpointDemoSlowGet } from '@/src/gen/hooks';
import { DemoSection } from './DemoSection';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';

export function LoadingDemo() {
  const t = useTranslations('demo.loading');
  const [hasTriggered, setHasTriggered] = useState(false);

  const { data, isFetching, refetch } = useSlowEndpointDemoSlowGet(
    { delay_ms: 2000 },
    { query: { enabled: hasTriggered } }
  );

  // Only show loading when actually fetching (not when query is just disabled)
  const isLoading = hasTriggered && isFetching;

  const triggerLoad = () => {
    setHasTriggered(true);
    void refetch();
  };

  return (
    <DemoSection icon="&#9203;" title={t('title')}>
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-sm">
          <span className="font-mono">isFetching:</span>
          <span className={isLoading
              ? 'text-yellow-500 motion-preset-pulse motion-duration-[1s] motion-loop-infinite'
              : 'text-green-500'}>
            {String(isLoading)}
          </span>
        </div>

        <div className="bg-muted rounded-lg p-4 min-h-[80px]">
          {isLoading ? (
            <>
              <Skeleton className="h-4 w-3/4 mb-2" />
              <Skeleton className="h-4 w-1/2" />
            </>
          ) : data ? (
            <div className="motion-preset-fade motion-preset-slide-up-sm motion-duration-[0.3s]">
              <p className="font-medium">{data.message}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {t('loadedAt')}: {data.timestamp}
              </p>
            </div>
          ) : (
            <p className="text-muted-foreground">{t('clickToLoad')}</p>
          )}
        </div>

        <div className="flex gap-2">
          <Button
            disabled={isLoading}
            onClick={triggerLoad}
            className="active:scale-95 hover:-translate-y-0.5 hover:shadow-md hover:shadow-primary/20 transition-all duration-150"
          >
            {isLoading ? t('loading') : t('trigger')}
          </Button>
        </div>
      </div>
    </DemoSection>
  );
}
