'use client';

import { Suspense, useState } from 'react';
import { useQueryClient, useQueryErrorResetBoundary } from '@tanstack/react-query';
import { ErrorBoundary } from 'react-error-boundary';
import { useTranslations } from 'next-intl';

import { useGetItemDetailDemoItemsItemIdGetSuspense } from '@/src/gen/hooks';
import { DemoSection } from './DemoSection';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';

function SuspenseContent({ itemId }: { itemId: number }) {
  const { data } = useGetItemDetailDemoItemsItemIdGetSuspense(itemId, {
    delay_ms: 1000,
  });

  return (
    <div className="motion-preset-fade motion-preset-slide-up-sm motion-duration-[0.3s]">
      <p className="font-semibold">{data.title}</p>
      <p className="text-sm text-muted-foreground">{data.description}</p>
    </div>
  );
}

function LoadingFallback() {
  const t = useTranslations('demo.suspense');
  return (
    <div className="space-y-2 animate-pulse">
      <Skeleton className="h-5 w-1/2" />
      <Skeleton className="h-4 w-3/4" />
      <p className="text-xs text-blue-500 mt-2">{t('suspenseLoading')}</p>
    </div>
  );
}

function ErrorFallback({
  resetErrorBoundary,
}: {
  resetErrorBoundary: () => void;
}) {
  const t = useTranslations('demo.suspense');
  return (
    <Alert variant="destructive" className="motion-preset-shake motion-duration-[0.4s]">
      <AlertDescription className="flex items-center justify-between">
        <span>{t('errorOccurred')}</span>
        <Button
          size="sm"
          variant="outline"
          onClick={resetErrorBoundary}
          className="active:scale-95 hover:-translate-y-0.5 hover:shadow-md transition-all duration-150"
        >
          {t('retry')}
        </Button>
      </AlertDescription>
    </Alert>
  );
}

export function SuspenseDemo() {
  const t = useTranslations('demo.suspense');
  const queryClient = useQueryClient();
  const { reset } = useQueryErrorResetBoundary();
  const [selectedId, setSelectedId] = useState(1);
  const [key, setKey] = useState(0);

  const handleChangeItem = (newId: number) => {
    // Clear cache and increment key to force re-mount
    queryClient.removeQueries({
      queryKey: [{ url: '/demo/items/:item_id', params: { item_id: newId } }],
    });
    setSelectedId(newId);
    setKey((k) => k + 1);
  };

  return (
    <DemoSection icon="&#9200;" title={t('title')}>
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">{t('description')}</p>

        <div className="flex gap-2">
          {[1, 2, 3].map((id) => (
            <Button
              key={id}
              variant={selectedId === id ? 'default' : 'outline'}
              size="sm"
              className={`active:scale-95 hover:-translate-y-0.5 hover:shadow-md hover:shadow-primary/20 transition-all duration-150 ${
                selectedId === id ? 'motion-preset-pop motion-duration-[0.15s]' : ''
              }`}
              onClick={() => { handleChangeItem(id); }}
            >
              Item {id}
            </Button>
          ))}
        </div>

        <div className="bg-muted rounded-lg p-4 min-h-[80px]">
          <ErrorBoundary
            onReset={reset}
            fallbackRender={({ resetErrorBoundary }) => (
              <ErrorFallback resetErrorBoundary={resetErrorBoundary} />
            )}
          >
            <Suspense key={key} fallback={<LoadingFallback />}>
              <SuspenseContent itemId={selectedId} />
            </Suspense>
          </ErrorBoundary>
        </div>

        <div className="bg-card border rounded-lg p-3">
          <p className="text-xs font-medium mb-2">{t('howItWorks')}:</p>
          <ul className="text-xs text-muted-foreground space-y-1">
            <li>• {t('point1')}</li>
            <li>• {t('point2')}</li>
            <li>• {t('point3')}</li>
          </ul>
        </div>

        <p className="text-xs text-muted-foreground">{t('note')}</p>
      </div>
    </DemoSection>
  );
}
