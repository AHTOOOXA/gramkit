'use client';

import { useTranslations } from 'next-intl';

import { Badge } from '@/components/ui/badge';

/**
 * BroadcastStatusBadge — active / completed status pill for a broadcast. The
 * backend reports an expired row as inactive, so it reads "Completed".
 *
 * Port of template-vue's `BroadcastStatusBadge.vue`.
 */
export function BroadcastStatusBadge({ isActive }: { isActive: boolean }) {
  const t = useTranslations('admin');
  return (
    <Badge variant={isActive ? 'default' : 'secondary'}>
      {isActive
        ? t('broadcasts.status.active')
        : t('broadcasts.status.completed')}
    </Badge>
  );
}
