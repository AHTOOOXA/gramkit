'use client';

import { useState, useEffect } from 'react';
import { onlineManager } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { Wifi, WifiOff } from 'lucide-react';

import {
  isApiError,
  getErrorMessage,
} from '@tma-platform/core-react/errors';
import { useGetServerTimeDemoTimeGet } from '@/src/gen/hooks';
import { DemoSection } from './DemoSection';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';

export function NetworkStatusDemo() {
  const t = useTranslations('demo.network');
  const [isOnline, setIsOnline] = useState(true);
  const [simulatedOffline, setSimulatedOffline] = useState(false);

  const { data, error, isFetching, isError, refetch, isPaused } =
    useGetServerTimeDemoTimeGet({
      query: {
        retry: 2,
        retryDelay: 1000,
      },
    });

  useEffect(() => {
    // Subscribe to online status changes
    const unsubscribe = onlineManager.subscribe((online) => {
      setIsOnline(online);
    });

    // Set initial state
    setIsOnline(onlineManager.isOnline());

    return () => {
      unsubscribe();
    };
  }, []);

  const toggleSimulatedOffline = () => {
    const newState = !simulatedOffline;
    setSimulatedOffline(newState);
    onlineManager.setOnline(!newState);
  };

  // Extract ApiError properties
  const apiError = isApiError(error) ? error : null;

  const getStatusColor = () => {
    if (simulatedOffline || !isOnline) return 'text-red-500';
    if (isFetching) return 'text-blue-500';
    if (isError) return 'text-yellow-500';
    return 'text-green-500';
  };

  const getStatusText = () => {
    if (simulatedOffline) return t('simulatedOffline');
    if (!isOnline) return t('offline');
    if (isPaused) return t('paused');
    if (isFetching) return t('fetching');
    if (isError) return t('error');
    return t('online');
  };

  return (
    <DemoSection icon="&#128225;" title={t('title')}>
      <div className="space-y-4">
        <div className="flex items-center gap-4 flex-wrap">
          <div className={`flex items-center gap-2 ${getStatusColor()}`}>
            <span className={`w-2 h-2 rounded-full ${
              isOnline && !simulatedOffline
                ? 'bg-green-500 animate-pulse'
                : 'bg-red-500'
            }`} />

            {isOnline && !simulatedOffline ? (
              <Wifi className="w-5 h-5 motion-preset-pulse motion-duration-[2s] motion-loop-infinite" />
            ) : (
              <WifiOff className="w-5 h-5 motion-preset-shake motion-duration-[0.5s]" />
            )}
            <span className="font-medium">{getStatusText()}</span>
          </div>

          {/* Show error classification when offline */}
          {(simulatedOffline || !isOnline) && (
            <Badge variant="outline" className="text-xs font-mono">
              classifies as: OFFLINE
            </Badge>
          )}
        </div>

        <div className="bg-muted rounded-lg p-4">
          {isPaused ? (
            <div className="space-y-3">
              <Alert className="motion-preset-slide-up-sm motion-preset-fade motion-duration-[0.3s]">
                <AlertDescription className="flex items-center justify-between">
                  <span>{t('queryPaused')}</span>
                  <span className="text-xs text-muted-foreground">
                    {t('willRetryWhenOnline')}
                  </span>
                </AlertDescription>
              </Alert>

              {/* Network error classification info */}
              <div className="bg-background/50 rounded-md p-3 text-xs font-mono space-y-1 border">
                <div className="text-muted-foreground mb-2 font-sans text-xs font-medium">
                  Network Error Classification:
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">code:</span>
                  <Badge variant="secondary" className="text-xs h-5">OFFLINE</Badge>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">recoverable:</span>
                  <Badge variant="default" className="text-xs h-5">true</Badge>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">behavior:</span>
                  <span className="text-foreground">Query paused, auto-resumes</span>
                </div>
              </div>
            </div>
          ) : isError ? (
            <div className="space-y-3">
              <Alert variant="destructive" className="motion-preset-shake motion-duration-[0.4s]">
                <AlertDescription>{getErrorMessage(error)}</AlertDescription>
              </Alert>

              {/* Show ApiError properties if available */}
              {apiError && (
                <div className="bg-background/50 rounded-md p-3 text-xs font-mono space-y-1 border">
                  <div className="text-muted-foreground mb-2 font-sans text-xs font-medium">
                    ApiError Properties:
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">status:</span>
                    <Badge variant="secondary" className="text-xs h-5">
                      {apiError.status}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">recoverable:</span>
                    <Badge variant={apiError.recoverable ? 'default' : 'secondary'} className="text-xs h-5">
                      {String(apiError.recoverable)}
                    </Badge>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center">
              <p
                className="text-2xl font-mono font-bold motion-preset-pop motion-duration-[0.2s]"
                key={data?.formatted}
              >
                {data?.formatted ?? '--:--:--'}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {t('serverTime')}
              </p>
            </div>
          )}
        </div>

        <div className="flex gap-2 flex-wrap">
          <Button
            variant={simulatedOffline ? 'destructive' : 'outline'}
            className="active:scale-95 hover:-translate-y-0.5 hover:shadow-md transition-all duration-150"
            onClick={toggleSimulatedOffline}
          >
            {simulatedOffline ? (
              <>
                <WifiOff className="w-4 h-4 mr-2" />
                {t('goOnline')}
              </>
            ) : (
              <>
                <Wifi className="w-4 h-4 mr-2" />
                {t('simulateOffline')}
              </>
            )}
          </Button>
          <Button
            variant="outline"
            disabled={isFetching || simulatedOffline}
            className="active:scale-95 hover:-translate-y-0.5 hover:shadow-md transition-all duration-150"
            onClick={() => refetch()}
          >
            {t('refetch')}
          </Button>
        </div>

        <p className="text-xs text-muted-foreground">{t('note')}</p>
      </div>
    </DemoSection>
  );
}
