'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { useGetServerTimeDemoTimeGet } from '@/src/gen/hooks';
import { DemoSection } from './DemoSection';
import { Button } from '@/components/ui/button';

const POLL_INTERVALS = [
  { label: 'Off', value: 0 },
  { label: '1s', value: 1000 },
  { label: '2s', value: 2000 },
  { label: '5s', value: 5000 },
];

export function PollingDemo() {
  const t = useTranslations('demo.polling');
  const [pollInterval, setPollInterval] = useState(0);

  const { data, isFetching, dataUpdatedAt } = useGetServerTimeDemoTimeGet({
    query: {
      refetchInterval: pollInterval > 0 ? pollInterval : false,
      refetchIntervalInBackground: false,
    },
  });

  return (
    <DemoSection icon="&#128260;" title={t('title')}>
      <div className="space-y-4">
        <div className="flex items-center gap-4 text-sm">
          <span className="flex items-center gap-2">
            <span className="font-mono">polling:</span>
            <span className={`inline-flex items-center gap-1.5 ${
              pollInterval > 0 ? 'text-green-500' : 'text-muted-foreground'
            }`}>
              {pollInterval > 0 && (
                <span className="w-2 h-2 bg-green-500 rounded-full motion-preset-pulse motion-duration-[1s] motion-loop-infinite" />
              )}
              {pollInterval > 0 ? `${String(pollInterval)}ms` : 'off'}
            </span>
          </span>
          <span>
            <span className="font-mono">isFetching:</span>{' '}
            <span className={isFetching ? 'text-blue-500' : 'text-muted-foreground'}>
              {String(isFetching)}
            </span>
          </span>
        </div>

        <div className={`bg-muted rounded-lg p-4 transition-shadow duration-500 ${
          pollInterval > 0 ? 'animate-pulse-glow' : ''
        }`}>
          <div className="text-center">
            <p
              className="text-4xl font-mono font-bold motion-preset-fade motion-duration-[0.15s]"
              key={data?.formatted}
            >
              {data?.formatted ?? '--:--:--'}
            </p>
            <p className="text-xs text-muted-foreground mt-2">
              {t('serverTime')}
            </p>
            {dataUpdatedAt && (
              <p className="text-xs text-muted-foreground">
                {t('lastUpdate')}: {new Date(dataUpdatedAt).toLocaleTimeString()}
              </p>
            )}
          </div>
        </div>

        <div className="flex gap-2 flex-wrap">
          {POLL_INTERVALS.map((interval) => (
            <Button
              key={interval.value}
              variant={pollInterval === interval.value ? 'default' : 'outline'}
              size="sm"
              className={`active:scale-95 hover:-translate-y-0.5 hover:shadow-md hover:shadow-primary/20 transition-all duration-150 ${
                pollInterval === interval.value ? 'motion-preset-pop motion-duration-[0.15s]' : ''
              }`}
              onClick={() => { setPollInterval(interval.value); }}
            >
              {interval.label}
            </Button>
          ))}
        </div>

        <p className="text-xs text-muted-foreground">{t('note')}</p>
      </div>
    </DemoSection>
  );
}
