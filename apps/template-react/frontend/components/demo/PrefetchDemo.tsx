'use client';

import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import {
  useGetItemDetailDemoItemsItemIdGet,
  getItemDetailDemoItemsItemIdGetQueryOptions,
} from '@/src/gen/hooks';
import { DemoSection } from './DemoSection';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';

const ITEMS = [
  { id: 1, label: 'Item 1' },
  { id: 2, label: 'Item 2' },
  { id: 3, label: 'Item 3' },
];

export function PrefetchDemo() {
  const t = useTranslations('demo.prefetch');
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [prefetchedIds, setPrefetchedIds] = useState<Set<number>>(new Set());

  const { data, isFetching } = useGetItemDetailDemoItemsItemIdGet(
    selectedId ?? 0,
    { delay_ms: 800 },
    { query: { enabled: selectedId !== null } }
  );

  const handlePrefetch = async (itemId: number) => {
    if (prefetchedIds.has(itemId)) return;

    await queryClient.prefetchQuery(
      getItemDetailDemoItemsItemIdGetQueryOptions(itemId, { delay_ms: 800 })
    );
    setPrefetchedIds((prev) => new Set(prev).add(itemId));
  };

  const handleSelect = (itemId: number) => {
    setSelectedId(itemId);
  };

  return (
    <DemoSection icon="&#128640;" title={t('title')}>
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">{t('description')}</p>

        <div className="flex gap-2">
          {ITEMS.map((item) => (
            <Button
              key={item.id}
              variant={selectedId === item.id ? 'default' : 'outline'}
              size="sm"
              className="relative active:scale-95 hover:scale-105 hover:-translate-y-1 hover:shadow-lg hover:shadow-primary/25 transition-all duration-150"
              onMouseEnter={() => handlePrefetch(item.id)}
              onClick={() => { handleSelect(item.id); }}
            >
              {item.label}
              {prefetchedIds.has(item.id) && selectedId !== item.id && (
                <span className="absolute -top-1.5 -right-1.5 w-2.5 h-2.5 bg-green-500 rounded-full motion-preset-pop animate-pulse shadow-[0_0_8px_2px_rgba(34,197,94,0.6)]" />
              )}
            </Button>
          ))}
        </div>

        <div className="bg-muted rounded-lg p-4 min-h-[100px]">
          {selectedId === null ? (
            <p className="text-muted-foreground text-center">{t('hoverHint')}</p>
          ) : isFetching ? (
            <div className="animate-pulse">
              <Skeleton className="h-5 w-1/2 mb-2" />
              <Skeleton className="h-4 w-3/4 mb-2" />
              <Skeleton className="h-4 w-full" />
            </div>
          ) : data ? (
            <div className="motion-preset-fade motion-preset-slide-up-sm motion-duration-[0.25s]">
              <p className="font-semibold text-lg">{data.title}</p>
              <p className="text-sm text-muted-foreground mt-1">{data.description}</p>
              <p className="text-sm mt-2">{data.details}</p>
              <p className="text-xs text-muted-foreground mt-2">
                {t('fetchedAt')}: {data.fetched_at}
              </p>
            </div>
          ) : null}
        </div>

        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="w-2 h-2 bg-green-500 rounded-full" />
          <span>{t('prefetchedIndicator')}</span>
        </div>

        <p className="text-xs text-muted-foreground">{t('note')}</p>
      </div>
    </DemoSection>
  );
}
