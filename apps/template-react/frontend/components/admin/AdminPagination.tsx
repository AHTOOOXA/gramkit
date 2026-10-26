'use client';

import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useTranslations } from 'next-intl';

import { Button } from '@/components/ui/button';

export interface AdminPaginationProps {
  page: number;
  totalPages: number;
  total?: number;
  onPrev: () => void;
  onNext: () => void;
}

/**
 * AdminPagination — controlled prev/next pager driven by `useAdminList`.
 * Stateless: it reads page / totalPages and reports intent; the parent wires
 * those to `nextPage()` / `prevPage()`. On narrow screens the buttons drop
 * their text and keep the chevrons (the label stays as `aria-label`).
 *
 * Port of template-vue's `AdminPagination.vue`.
 * TODO: extract to core/frontend-react when a second React app needs this.
 */
export function AdminPagination({
  page,
  totalPages,
  total,
  onPrev,
  onNext,
}: AdminPaginationProps) {
  const t = useTranslations('admin');

  const canPrev = page > 1;
  const canNext = page < totalPages;

  return (
    <div className="flex items-center justify-between gap-3 pt-3 text-sm">
      <span className="text-muted-foreground min-w-0">
        {t('table.pageOf', { page, total: Math.max(totalPages, 1) })}
        {total !== undefined && (
          <>
            {' '}
            <span className="whitespace-nowrap">
              · {t('table.totalRows', { count: total })}
            </span>
          </>
        )}
      </span>
      <div className="flex shrink-0 items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          disabled={!canPrev}
          aria-label={t('table.prev')}
          onClick={onPrev}
        >
          <ChevronLeft className="h-4 w-4" />
          <span className="hidden sm:inline">{t('table.prev')}</span>
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={!canNext}
          aria-label={t('table.next')}
          onClick={onNext}
        >
          <span className="hidden sm:inline">{t('table.next')}</span>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
