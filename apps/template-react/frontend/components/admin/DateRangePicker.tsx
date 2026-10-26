'use client';

import { useTranslations } from 'next-intl';

import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export interface DateRange {
  from?: string;
  to?: string;
}

/**
 * DateRangePicker — two native date inputs reporting a `{ from, to }` pair of
 * ISO (YYYY-MM-DD) strings. Native `<input type="date">` avoids pulling in a
 * calendar and gives the platform picker inside Telegram on phones.
 *
 * Port of template-vue's `DateRangePicker.vue`.
 * TODO: extract to core/frontend-react when a second React app needs this.
 */
export function DateRangePicker({
  value,
  onChange,
}: {
  value: DateRange;
  onChange: (value: DateRange) => void;
}) {
  const t = useTranslations('admin');

  return (
    <div className="grid w-full grid-cols-2 gap-3 sm:flex sm:w-auto sm:items-end">
      <div className="flex min-w-0 flex-col gap-1">
        <Label className="text-muted-foreground text-xs">
          {t('filters.dateFrom')}
        </Label>
        <Input
          type="date"
          className="w-full sm:w-auto"
          value={value.from ?? ''}
          onChange={(e) => {
            onChange({ ...value, from: e.target.value || undefined });
          }}
        />
      </div>
      <div className="flex min-w-0 flex-col gap-1">
        <Label className="text-muted-foreground text-xs">
          {t('filters.dateTo')}
        </Label>
        <Input
          type="date"
          className="w-full sm:w-auto"
          value={value.to ?? ''}
          onChange={(e) => {
            onChange({ ...value, to: e.target.value || undefined });
          }}
        />
      </div>
    </div>
  );
}
