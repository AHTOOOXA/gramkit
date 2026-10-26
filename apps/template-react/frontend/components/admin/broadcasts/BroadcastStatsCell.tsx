'use client';

import { useTranslations } from 'next-intl';

import { cn } from '@/lib/utils';
import type { BroadcastDeliveryStats } from '@/src/gen/models/BroadcastDeliveryStats';

/**
 * BroadcastStatsCell — compact delivery counters for a broadcast (list rows and
 * the detail page).
 *
 * Telegram exposes neither read receipts nor clicks, so this only shows
 * sent / success / fail / cycles (never a fabricated CTR).
 *
 * Port of template-vue's `BroadcastStatsCell.vue`.
 */
export function BroadcastStatsCell({
  stats,
  className,
}: {
  stats: BroadcastDeliveryStats;
  className?: string;
}) {
  const t = useTranslations('admin');

  const successRate = stats.sent_count
    ? Math.round((stats.success_count / stats.sent_count) * 100)
    : null;

  return (
    <div className={cn('flex flex-col gap-0.5 text-xs', className)}>
      {stats.cycles_run === 0 ? (
        <span className="text-muted-foreground">
          {t('broadcasts.stats.notSentYet')}
        </span>
      ) : (
        <>
          <span className="text-foreground">
            {t('broadcasts.stats.delivered')}: {stats.success_count}/
            {stats.sent_count}
            {successRate !== null && (
              <span className="text-muted-foreground"> ({successRate}%)</span>
            )}
          </span>
          {stats.fail_count > 0 && (
            <span className="text-destructive">
              {t('broadcasts.stats.failed')}: {stats.fail_count}
            </span>
          )}
          <span className="text-muted-foreground">
            {t('broadcasts.stats.cycles')}: {stats.cycles_run}
          </span>
        </>
      )}
    </div>
  );
}
