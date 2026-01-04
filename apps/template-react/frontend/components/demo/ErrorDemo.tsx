'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  isApiError,
  getErrorMessage,
} from '@tma-platform/core-react/errors';
import { useUnreliableEndpointDemoUnreliableGet } from '@/src/gen/hooks';
import { DemoSection } from './DemoSection';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';

export function ErrorDemo() {
  const t = useTranslations('demo.error');
  const [hasTriggered, setHasTriggered] = useState(false);

  const { data, error, isFetching, refetch, failureCount } =
    useUnreliableEndpointDemoUnreliableGet(
      { fail_rate: 0.7 },
      {
        query: {
          enabled: hasTriggered,
          retry: 3,
          retryDelay: (attempt: number) => Math.min(1000 * 2 ** attempt, 5000),
        },
      }
    );

  // Only show loading when actually fetching (not when query is just disabled)
  const isLoading = hasTriggered && isFetching;

  // Extract ApiError properties if available
  const apiError = isApiError(error) ? error : null;

  const triggerRequest = () => {
    setHasTriggered(true);
    void refetch();
  };

  const renderContent = () => {
    if (isLoading) {
      return (
        <p className="text-muted-foreground animate-pulse">
          {t('trying')}...
        </p>
      );
    }
    if (error) {
      return (
        <div className="space-y-3">
          <Alert variant="destructive" className="motion-preset-shake motion-duration-[0.4s]">
            <AlertDescription className="flex items-center justify-between">
              <span>{getErrorMessage(error)}</span>
              <Button
                size="sm"
                variant="outline"
                className="active:scale-95 hover:-translate-y-0.5 hover:shadow-md transition-all duration-150"
                onClick={() => refetch()}
              >
                {t('retry')}
              </Button>
            </AlertDescription>
          </Alert>

          {/* ApiError properties display */}
          {apiError && (
            <div className="bg-background/50 rounded-md p-3 text-xs font-mono space-y-1 border">
              <div className="text-muted-foreground mb-2 font-sans text-xs font-medium">
                ApiError Properties:
              </div>
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">message:</span>
                <span className="text-foreground">&quot;{apiError.message}&quot;</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">recoverable:</span>
                <Badge variant={apiError.recoverable ? 'default' : 'secondary'} className="text-xs h-5">
                  {String(apiError.recoverable)}
                </Badge>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">status:</span>
                <span className="text-foreground">{apiError.status}</span>
              </div>
            </div>
          )}
        </div>
      );
    }

    if (data) {
      return (
        <p className="text-green-500 font-medium motion-preset-pop motion-duration-[0.3s]">
          {data.message}
        </p>
      );
    }
    return <p className="text-muted-foreground">{t('clickToTest')}</p>;
  };

  return (
    <DemoSection icon="&#10060;" title={t('title')}>
      <div className="space-y-4">
        <div className="flex items-center gap-4 text-sm flex-wrap">
          <span>
            <span className="font-mono">isError:</span>{' '}
            <span className={`transition-colors duration-200 ${error ? 'text-red-500' : 'text-green-500'}`}>
              {String(!!error)}
            </span>
          </span>
          <span>
            <span className="font-mono">retries:</span>{' '}
            <span className="motion-preset-pop motion-duration-[0.2s]" key={failureCount}>
              {failureCount}/3
            </span>
          </span>
          {apiError && (
            <span>
              <span className="font-mono">willRetry:</span>{' '}
              <span className={apiError.recoverable ? 'text-yellow-500' : 'text-red-500'}>
                {apiError.recoverable ? 'yes' : 'no'}
              </span>
            </span>
          )}
        </div>

        <div className="bg-muted rounded-lg p-4 min-h-[80px]">
          {renderContent()}
        </div>

        <Button
          disabled={isLoading}
          className="active:scale-95 hover:-translate-y-0.5 hover:shadow-md hover:shadow-primary/20 transition-all duration-150"
          onClick={triggerRequest}
        >
          {t('trigger')} (70% {t('failRate')})
        </Button>
      </div>
    </DemoSection>
  );
}
