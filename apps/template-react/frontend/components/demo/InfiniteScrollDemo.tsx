'use client';

import { useEffect, useRef } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import { getPaginatedItemsDemoItemsGet } from '@/src/gen/client/getPaginatedItemsDemoItemsGet';
import type { PaginatedResponse } from '@/src/gen/models/PaginatedResponse';
import { DemoSection } from './DemoSection';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';

export function InfiniteScrollDemo() {
  const t = useTranslations('demo.infiniteScroll');
  const sentinelRef = useRef<HTMLDivElement>(null);

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    refetch,
  } = useInfiniteQuery({
    queryKey: ['demo', 'infinite-items'],
    queryFn: async ({ pageParam }) => {
      return getPaginatedItemsDemoItemsGet({
        cursor: pageParam,
        limit: 5,
        delay_ms: 500,
      });
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage: PaginatedResponse) => lastPage.next_cursor,
  });

  // Auto-fetch on scroll using IntersectionObserver
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && hasNextPage && !isFetchingNextPage) {
          void fetchNextPage();
        }
      },
      { threshold: 0.1 }
    );

    observer.observe(sentinel);
    return () => { observer.disconnect(); };
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  const allItems = data?.pages.flatMap((page) => page.items) ?? [];
  const total = data?.pages[0]?.total ?? 0;

  return (
    <DemoSection icon="&#128214;" title={t('title')}>
      <div className="space-y-4">
        <div className="flex items-center gap-4 text-sm">
          <span>
            <span className="font-mono">loaded:</span>{' '}
            <span>{allItems.length}/{total}</span>
          </span>
          <span>
            <span className="font-mono">hasMore:</span>{' '}
            <span className={hasNextPage ? 'text-green-500' : 'text-muted-foreground'}>
              {String(hasNextPage)}
            </span>
          </span>
        </div>

        <div className="bg-muted rounded-lg p-3 max-h-[200px] overflow-y-auto space-y-2">
          {isLoading ? (
            <>
              <Skeleton className="h-10 w-full rounded animate-pulse" />
              <Skeleton className="h-10 w-full rounded animate-pulse" />
              <Skeleton className="h-10 w-full rounded animate-pulse" />
            </>
          ) : isError ? (
            <div className="text-center py-4 motion-preset-shake motion-duration-[0.4s]">
              <p className="text-destructive mb-2">{t('error')}</p>
              <Button
                size="sm"
                variant="outline"
                onClick={() => refetch()}
                className="active:scale-95 hover:-translate-y-0.5 hover:shadow-md transition-all duration-150"
              >
                {t('retry')}
              </Button>
            </div>
          ) : allItems.length === 0 ? (
            <p className="text-muted-foreground text-center py-4">{t('empty')}</p>
          ) : (
            <>
              {allItems.map((item, index) => (
                <div
                  key={item.id}
                  className="bg-background rounded p-2 text-sm motion-preset-slide-up motion-duration-[0.2s]"
                  style={{ animationDelay: `${String((index % 5) * 50)}ms` }}
                >
                  <span className="font-medium">{item.title}</span>
                  <span className="text-muted-foreground ml-2">- {item.description}</span>
                </div>
              ))}
              {/* Sentinel element for intersection observer */}
              <div ref={sentinelRef} className="h-1" />
            </>
          )}

          {isFetchingNextPage && (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full rounded animate-pulse" />
              <Skeleton className="h-10 w-full rounded animate-pulse" />
            </div>
          )}
        </div>

        <p className="text-xs text-muted-foreground">{t('note')}</p>
      </div>
    </DemoSection>
  );
}
