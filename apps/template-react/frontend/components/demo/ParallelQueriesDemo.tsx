'use client';

import { useQueries } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { Cloud, TrendingUp, Newspaper, RefreshCw } from 'lucide-react';

import {
  getWeatherDemoWeatherGetQueryOptions,
  getStockDemoStockGetQueryOptions,
  getNewsDemoNewsGetQueryOptions,
} from '@/src/gen/hooks';
import { DemoSection } from './DemoSection';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';

export function ParallelQueriesDemo() {
  const t = useTranslations('demo.parallel');

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
  });

  const [weatherQuery, stockQuery, newsQuery] = results;

  const isAnyFetching = results.some((r) => r.isFetching);
  const loadedCount = results.filter((r) => r.data).length;

  const refetchAll = () => {
    results.forEach((r) => { void r.refetch(); });
  };

  return (
    <DemoSection icon="&#9881;" title={t('title')}>
      <div className="space-y-4">
        <div className="flex items-center gap-4 text-sm">
          <span>
            <span className="font-mono">loaded:</span>{' '}
            <span>{loadedCount}/3</span>
          </span>
          <span>
            <span className="font-mono">fetching:</span>{' '}
            <span className={isAnyFetching ? 'text-blue-500' : 'text-muted-foreground'}>
              {String(isAnyFetching)}
            </span>
          </span>
        </div>

        <div className="grid gap-3">
          {/* Weather Card */}
          <div
            className="bg-muted rounded-lg p-3 motion-preset-slide-up motion-duration-[0.3s]"
            style={{ animationDelay: '0ms' }}
          >
            <div className="flex items-center gap-2 mb-2">
              <Cloud className="w-4 h-4 text-blue-500" />
              <span className="text-sm font-medium">{t('weather')}</span>
              {weatherQuery.isFetching && (
                <span className="text-xs text-blue-500 ml-auto animate-pulse">{t('loading')}</span>
              )}
            </div>
            {weatherQuery.isLoading ? (
              <Skeleton className="h-8 w-full" />
            ) : weatherQuery.data ? (
              <div className="flex items-baseline gap-2 motion-preset-fade motion-duration-[0.2s]">
                <span className="text-2xl font-bold">{weatherQuery.data.temperature}°C</span>
                <span className="text-muted-foreground">{weatherQuery.data.condition}</span>
                <span className="text-xs text-muted-foreground ml-auto">
                  {weatherQuery.data.city}
                </span>
              </div>
            ) : null}
          </div>

          {/* Stock Card */}
          <div
            className="bg-muted rounded-lg p-3 motion-preset-slide-up motion-duration-[0.3s]"
            style={{ animationDelay: '100ms' }}
          >
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="w-4 h-4 text-green-500" />
              <span className="text-sm font-medium">{t('stock')}</span>
              {stockQuery.isFetching && (
                <span className="text-xs text-blue-500 ml-auto animate-pulse">{t('loading')}</span>
              )}
            </div>
            {stockQuery.isLoading ? (
              <Skeleton className="h-8 w-full" />
            ) : stockQuery.data ? (
              <div className="flex items-baseline gap-2 motion-preset-fade motion-duration-[0.2s]">
                <span className="text-2xl font-bold">${stockQuery.data.price}</span>
                <span
                  className={
                    stockQuery.data.change >= 0
                      ? 'text-green-500 motion-preset-bounce motion-duration-[0.3s]'
                      : 'text-red-500 motion-preset-shake motion-duration-[0.3s]'
                  }
                  key={stockQuery.data.change}
                >
                  {stockQuery.data.change >= 0 ? '+' : ''}
                  {stockQuery.data.change}%
                </span>
                <span className="text-xs text-muted-foreground ml-auto">
                  {stockQuery.data.symbol}
                </span>
              </div>
            ) : null}
          </div>

          {/* News Card */}
          <div
            className="bg-muted rounded-lg p-3 motion-preset-slide-up motion-duration-[0.3s]"
            style={{ animationDelay: '200ms' }}
          >
            <div className="flex items-center gap-2 mb-2">
              <Newspaper className="w-4 h-4 text-orange-500" />
              <span className="text-sm font-medium">{t('news')}</span>
              {newsQuery.isFetching && (
                <span className="text-xs text-blue-500 ml-auto animate-pulse">{t('loading')}</span>
              )}
            </div>
            {newsQuery.isLoading ? (
              <Skeleton className="h-8 w-full" />
            ) : newsQuery.data ? (
              <div className="motion-preset-fade motion-duration-[0.2s]">
                <p className="text-sm font-medium line-clamp-1">
                  {newsQuery.data.headline}
                </p>
                <p className="text-xs text-muted-foreground">{newsQuery.data.source}</p>
              </div>
            ) : null}
          </div>
        </div>

        <Button
          variant="outline"
          disabled={isAnyFetching}
          className="w-full active:scale-[0.98] hover:-translate-y-0.5 hover:shadow-md transition-all duration-150"
          onClick={refetchAll}
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${isAnyFetching ? 'animate-spin' : ''}`} />
          {t('refetchAll')}
        </Button>

        <p className="text-xs text-muted-foreground">{t('note')}</p>
      </div>
    </DemoSection>
  );
}
