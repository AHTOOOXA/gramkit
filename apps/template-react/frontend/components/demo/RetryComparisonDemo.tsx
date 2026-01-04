'use client';

import { useState, useEffect, useRef } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';
import { RefreshCw, XCircle, CheckCircle } from 'lucide-react';

import { getErrorMessage } from '@tma-platform/core-react/errors';
import { triggerErrorDemoErrorStatusCodeGet } from '@/src/gen/client/triggerErrorDemoErrorStatusCodeGet';
import { DemoSection } from './DemoSection';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface AttemptLog {
  attempt: number;
  timestamp: number;
  status: 'pending' | 'failed' | 'success';
}

interface QueryPanelProps {
  title: string;
  statusCode: number;
  recoverable: boolean;
  isActive: boolean;
  onTrigger: () => void;
  attempts: AttemptLog[];
  error: unknown;
  isFetching: boolean;
}

function QueryPanel({
  title,
  statusCode,
  recoverable,
  isActive,
  onTrigger,
  attempts,
  error,
  isFetching,
}: QueryPanelProps) {
  const t = useTranslations('demo.retryComparison');

  return (
    <div className="flex-1 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-sm">{title}</h4>
        <Badge variant={recoverable ? 'default' : 'secondary'} className="text-xs">
          {recoverable ? t('willRetry') : t('noRetry')}
        </Badge>
      </div>

      <div className="text-xs text-muted-foreground space-y-1">
        <div>
          <span className="font-mono">status:</span> {statusCode}
        </div>
        <div>
          <span className="font-mono">recoverable:</span> {String(recoverable)}
        </div>
      </div>

      <Button
        size="sm"
        variant="outline"
        disabled={isFetching}
        className="w-full active:scale-95 transition-transform"
        onClick={onTrigger}
      >
        {isFetching ? (
          <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
        ) : null}
        {t('trigger')}
      </Button>

      {/* Timeline */}
      <div className="bg-muted/50 rounded-lg p-3 min-h-[140px] space-y-2">
        {!isActive && attempts.length === 0 && (
          <div className="text-xs text-muted-foreground text-center py-8">
            {t('clickToStart')}
          </div>
        )}

        {attempts.map((attempt, idx) => (
          <div
            key={idx}
            className="flex items-center gap-2 text-xs motion-preset-slide-right motion-duration-[0.2s]"
            style={{ animationDelay: `${String(idx * 100)}ms` }}
          >
            {attempt.status === 'pending' ? (
              <RefreshCw className="w-3 h-3 text-blue-500 animate-spin" />
            ) : attempt.status === 'failed' ? (
              <XCircle className="w-3 h-3 text-red-500" />
            ) : (
              <CheckCircle className="w-3 h-3 text-green-500" />
            )}
            <span className="font-mono">
              {t('attempt')} {attempt.attempt}
            </span>
            {attempt.status === 'failed' && (
              <span className="text-red-500">{t('failed')}</span>
            )}
            {attempt.status === 'success' && (
              <span className="text-green-500">{t('success')}</span>
            )}
          </div>
        ))}

        {Boolean(error) && !isFetching && (
          <div className="text-xs text-red-500 pt-2 border-t mt-2">
            {getErrorMessage(error)}
          </div>
        )}
      </div>
    </div>
  );
}

export function RetryComparisonDemo() {
  const t = useTranslations('demo.retryComparison');

  // State for tracking attempts
  const [attempts500, setAttempts500] = useState<AttemptLog[]>([]);
  const [attempts404, setAttempts404] = useState<AttemptLog[]>([]);
  const [active500, setActive500] = useState(false);
  const [active404, setActive404] = useState(false);

  const attempt500Ref = useRef(0);
  const attempt404Ref = useRef(0);

  // Query for 500 error (will retry)
  const query500 = useQuery({
    queryKey: ['demo-error-500', active500],
    queryFn: async () => {
      attempt500Ref.current += 1;
      const currentAttempt = attempt500Ref.current;

      setAttempts500((prev) => [
        ...prev,
        { attempt: currentAttempt, timestamp: Date.now(), status: 'pending' },
      ]);

      try {
        await triggerErrorDemoErrorStatusCodeGet(500);
        setAttempts500((prev) =>
          prev.map((a) =>
            a.attempt === currentAttempt ? { ...a, status: 'success' } : a
          )
        );
        return { success: true };
      } catch (error) {
        setAttempts500((prev) =>
          prev.map((a) =>
            a.attempt === currentAttempt ? { ...a, status: 'failed' } : a
          )
        );
        throw error;
      }
    },
    enabled: active500,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 5000),
  });

  // Query for 404 error (no retry)
  const query404 = useQuery({
    queryKey: ['demo-error-404', active404],
    queryFn: async () => {
      attempt404Ref.current += 1;
      const currentAttempt = attempt404Ref.current;

      setAttempts404((prev) => [
        ...prev,
        { attempt: currentAttempt, timestamp: Date.now(), status: 'pending' },
      ]);

      try {
        await triggerErrorDemoErrorStatusCodeGet(404);
        setAttempts404((prev) =>
          prev.map((a) =>
            a.attempt === currentAttempt ? { ...a, status: 'success' } : a
          )
        );
        return { success: true };
      } catch (error) {
        setAttempts404((prev) =>
          prev.map((a) =>
            a.attempt === currentAttempt ? { ...a, status: 'failed' } : a
          )
        );
        throw error;
      }
    },
    enabled: active404,
    // Uses default retry from QueryClient which checks recoverable
  });

  const trigger500 = () => {
    attempt500Ref.current = 0;
    setAttempts500([]);
    setActive500(true);
  };

  const trigger404 = () => {
    attempt404Ref.current = 0;
    setAttempts404([]);
    setActive404(true);
  };

  // Reset active state when queries settle
  useEffect(() => {
    if (!query500.isFetching && active500) {
      // Keep active for a moment to show final state
      const timer = setTimeout(() => { setActive500(false); }, 500);
      return () => { clearTimeout(timer); };
    }
  }, [query500.isFetching, active500]);

  useEffect(() => {
    if (!query404.isFetching && active404) {
      const timer = setTimeout(() => { setActive404(false); }, 500);
      return () => { clearTimeout(timer); };
    }
  }, [query404.isFetching, active404]);

  return (
    <DemoSection icon="&#128260;" title={t('title')}>
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          {t('description')}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <QueryPanel
            title={t('serverError')}
            statusCode={500}
            recoverable={true}
            isActive={active500}
            onTrigger={trigger500}
            attempts={attempts500}
            error={query500.error}
            isFetching={query500.isFetching}
          />

          <QueryPanel
            title={t('notFound')}
            statusCode={404}
            recoverable={false}
            isActive={active404}
            onTrigger={trigger404}
            attempts={attempts404}
            error={query404.error}
            isFetching={query404.isFetching}
          />
        </div>

        <div className="text-xs text-muted-foreground bg-muted/50 rounded-lg p-3">
          <strong>{t('note')}:</strong> {t('noteText')}
        </div>
      </div>
    </DemoSection>
  );
}
