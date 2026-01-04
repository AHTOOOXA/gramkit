'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useMutation } from '@tanstack/react-query';

import {
  isApiError,
  getErrorMessage,
} from '@tma-platform/core-react/errors';
import { triggerErrorDemoErrorStatusCodeGet } from '@/src/gen/client/triggerErrorDemoErrorStatusCodeGet';
import { DemoSection } from './DemoSection';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';

// HTTP status codes to demo
const STATUS_CODES = [
  { code: 400, label: '400', description: 'Bad Request' },
  { code: 401, label: '401', description: 'Unauthorized' },
  { code: 403, label: '403', description: 'Forbidden' },
  { code: 404, label: '404', description: 'Not Found' },
  { code: 409, label: '409', description: 'Conflict' },
  { code: 422, label: '422', description: 'Validation' },
  { code: 429, label: '429', description: 'Rate Limit' },
  { code: 500, label: '500', description: 'Server Error' },
  { code: 503, label: '503', description: 'Unavailable' },
] as const;

interface ErrorInfo {
  statusCode: number;
  message: string;
  recoverable: boolean;
  willRetry: boolean;
}

export function HttpStatusDemo() {
  const t = useTranslations('demo.httpStatus');
  const [lastError, setLastError] = useState<ErrorInfo | null>(null);
  const [activeCode, setActiveCode] = useState<number | null>(null);

  const mutation = useMutation({
    mutationFn: async (statusCode: number) => {
      setActiveCode(statusCode);
      // Uses generated client - error gets classified by axios interceptor
      await triggerErrorDemoErrorStatusCodeGet(statusCode);
    },
    onError: (error) => {
      if (isApiError(error)) {
        setLastError({
          statusCode: error.status,
          message: error.message,
          recoverable: error.recoverable,
          willRetry: error.recoverable,
        });
      } else {
        setLastError({
          statusCode: activeCode ?? 0,
          message: getErrorMessage(error),
          recoverable: false,
          willRetry: false,
        });
      }
      setActiveCode(null);
    },
  });

  const triggerError = (statusCode: number) => {
    setLastError(null);
    mutation.mutate(statusCode);
  };

  const getButtonVariant = (code: number) => {
    if (code >= 500) return 'destructive';
    if (code === 401 || code === 403) return 'secondary';
    return 'outline';
  };

  return (
    <DemoSection icon="&#128679;" title={t('title')}>
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          {t('description')}
        </p>

        {/* Status code buttons */}
        <div className="flex flex-wrap gap-2">
          {STATUS_CODES.map(({ code, label, description }) => (
            <Button
              key={code}
              variant={getButtonVariant(code)}
              size="sm"
              disabled={mutation.isPending}
              className="text-xs active:scale-95 transition-transform"
              onClick={() => { triggerError(code); }}
            >
              {activeCode === code ? (
                <span className="animate-pulse">...</span>
              ) : (
                <>
                  <span className="font-mono font-bold">{label}</span>
                  <span className="ml-1 opacity-70 hidden sm:inline">{description}</span>
                </>
              )}
            </Button>
          ))}
        </div>

        {/* Result display */}
        <div className="bg-muted rounded-lg p-4 min-h-[120px]">
          {lastError ? (
            <div className="space-y-3 motion-preset-fade motion-duration-[0.3s]">
              <Alert variant="destructive">
                <AlertDescription className="font-mono text-sm">
                  {lastError.message}
                </AlertDescription>
              </Alert>

              {/* Classification details */}
              <div className="bg-background/50 rounded-md p-3 text-xs font-mono space-y-2 border">
                <div className="text-muted-foreground mb-2 font-sans text-xs font-medium">
                  Error Classification:
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">status:</span>
                    <Badge variant="outline" className="text-xs h-5 font-mono">
                      {lastError.statusCode}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">recoverable:</span>
                    <Badge
                      variant={lastError.recoverable ? 'default' : 'secondary'}
                      className="text-xs h-5"
                    >
                      {String(lastError.recoverable)}
                    </Badge>
                  </div>
                </div>
                <div className="flex items-center gap-2 pt-1 border-t">
                  <span className="text-muted-foreground">TanStack Query:</span>
                  <span className={lastError.willRetry ? 'text-yellow-500' : 'text-muted-foreground'}>
                    {lastError.willRetry ? 'Will retry (server error)' : 'No retry (client error)'}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
              {t('clickToTest')}
            </div>
          )}
        </div>

        {/* Legend */}
        <div className="text-xs text-muted-foreground space-y-1">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">4xx</Badge>
            <span>{t('clientErrors')}</span>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="destructive" className="text-xs">5xx</Badge>
            <span>{t('serverErrors')}</span>
          </div>
        </div>
      </div>
    </DemoSection>
  );
}
