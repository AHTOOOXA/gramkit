'use client';

import { type ReactNode } from 'react';
import { useTranslations } from 'next-intl';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';

export interface AdminStateBlockProps {
  isLoading?: boolean;
  error?: unknown;
  isEmpty?: boolean;
  /** How many skeleton rows the default loading state renders. */
  skeletonRows?: number;
  /** Custom skeleton for the loading state. */
  loading?: ReactNode;
  /** Custom placeholder for the empty state. */
  empty?: ReactNode;
  onRetry?: () => void;
  children?: ReactNode;
}

/**
 * AdminStateBlock — the canonical async-state wrapper for every admin section.
 *
 * Branch order is fixed and exact: isLoading → error → empty → children.
 * (A failed refetch that still has stale data is treated as an error here so
 * the retry affordance is always reachable.)
 *
 * Port of template-vue's `AdminStateBlock.vue`.
 * TODO: extract to core/frontend-react when a second React app needs this.
 */
export function AdminStateBlock({
  isLoading = false,
  error,
  isEmpty = false,
  skeletonRows = 5,
  loading,
  empty,
  onRetry,
  children,
}: AdminStateBlockProps) {
  const t = useTranslations('admin');

  // 1. Loading
  if (isLoading) {
    return (
      <div>
        {loading ?? (
          <div className="space-y-2">
            {Array.from({ length: skeletonRows }, (_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        )}
      </div>
    );
  }

  // 2. Error
  if (error) {
    return (
      <Alert
        variant="destructive"
        className="motion-preset-shake motion-duration-[0.4s]"
      >
        <AlertDescription className="flex items-center justify-between gap-3">
          <span>{t('state.error')}</span>
          <Button size="sm" variant="outline" onClick={onRetry}>
            {t('state.retry')}
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  // 3. Empty
  if (isEmpty) {
    return (
      <div>
        {empty ?? <AdminEmptyState>{t('state.empty')}</AdminEmptyState>}
      </div>
    );
  }

  // 4. Data
  return <>{children}</>;
}

/** The dashed "nothing here" box the admin screens use for empty states. */
export function AdminEmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="border-border text-muted-foreground flex flex-col items-center justify-center rounded-xl border border-dashed py-12 text-center text-sm">
      {children}
    </div>
  );
}
