'use client';

import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { Search } from 'lucide-react';
import { useTranslations } from 'next-intl';

import { type AdminListFilters } from '@/hooks/useAdminList';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { Input } from '@/components/ui/input';

import { DateRangePicker } from './DateRangePicker';

export interface AdminFilterBarProps {
  filters: AdminListFilters;
  onFiltersChange: (next: AdminListFilters) => void;
  searchable?: boolean;
  /** Section-specific filters (e.g. an `action` Select). */
  children?: ReactNode;
}

/**
 * AdminFilterBar — free-text search + a date range over an `AdminListFilters`
 * bag (the same shape `useAdminList` owns). Section filters go in `children`;
 * the parent merges them into the same object.
 *
 * Mobile-first: search takes the full row, section filters and the two dates
 * wrap below it; from `sm` up everything sits on one wrapping line.
 *
 * Search is debounced (300 ms): every keystroke would otherwise refetch the
 * list and reset the page. The emitting effect depends on the debounced value
 * only and reads the current filters through a ref, so an outside reset of
 * `filters.search` is never undone by the old debounced text. A second effect
 * copies outside changes of `filters.search` into the input.
 *
 * Port of template-vue's `AdminFilterBar.vue`.
 * TODO: extract to core/frontend-react when a second React app needs this.
 */
export function AdminFilterBar({
  filters,
  onFiltersChange,
  searchable = true,
  children,
}: AdminFilterBarProps) {
  const t = useTranslations('admin');

  const [search, setSearch] = useState(filters.search ?? '');
  const debounced = useDebouncedValue(search, 300);

  // Latest props for the debounced effect, without making them its deps.
  const filtersRef = useRef(filters);
  const onChangeRef = useRef(onFiltersChange);
  useLayoutEffect(() => {
    filtersRef.current = filters;
    onChangeRef.current = onFiltersChange;
  });

  // Follow outside changes (e.g. a reset by the parent).
  const outsideSearch = filters.search ?? '';
  useEffect(() => {
    setSearch(outsideSearch);
  }, [outsideSearch]);

  useEffect(() => {
    const current = filtersRef.current;
    if (debounced !== (current.search ?? '')) {
      onChangeRef.current({ ...current, search: debounced });
    }
  }, [debounced]);

  return (
    <div className="border-border bg-card flex flex-wrap items-end gap-3 rounded-xl border p-3">
      {searchable && (
        <div className="relative w-full sm:w-auto sm:min-w-[12rem] sm:flex-1">
          <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
          <Input
            type="search"
            value={search}
            placeholder={t('filters.searchPlaceholder')}
            className="pl-9"
            onChange={(e) => {
              setSearch(e.target.value);
            }}
          />
        </div>
      )}

      {children}

      <DateRangePicker
        value={{ from: filters.date_from, to: filters.date_to }}
        onChange={(value) => {
          onFiltersChange({
            ...filters,
            date_from: value.from,
            date_to: value.to,
          });
        }}
      />
    </div>
  );
}
