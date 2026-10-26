'use client';

import { Fragment, type MouseEvent, type ReactNode } from 'react';
import { ArrowDown, ArrowUp, ChevronsUpDown } from 'lucide-react';
import { useTranslations } from 'next-intl';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

import { AdminPagination } from './AdminPagination';
import { AdminStateBlock } from './AdminStateBlock';

export interface AdminColumn<T> {
  /** Stable key — also the sort column id and the default cell's field. */
  key: string;
  /** Header label (already translated by the caller). An empty label marks an
   *  actions column: on phones it sits next to the card title. */
  label: string;
  /** Enable click-to-sort on this column header. */
  sortable?: boolean;
  /** Extra classes for the cell + header (alignment, width). */
  className?: string;
  /** What the column means — shown on hovering the header (dotted underline marks it). */
  hint?: string;
  /** Custom cell (Vue's `#cell-<key>` slot); defaults to `row[key]`. */
  cell?: (row: T) => ReactNode;
}

export interface AdminDataTableProps<T> {
  columns: AdminColumn<T>[];
  rows: T[];
  rowKey?: (row: T) => string | number;
  isLoading?: boolean;
  error?: unknown;
  sortBy?: string | null;
  sortDir?: 'asc' | 'desc';
  page?: number;
  totalPages?: number;
  total?: number;
  /** Smaller text and tighter cells, for wide tables with many columns. */
  dense?: boolean;
  /** Hide the pagination footer (for short, unpaginated lists). */
  hidePagination?: boolean;
  /** Make whole rows (cards on phones) clickable. */
  onRowClick?: (row: T) => void;
  onSort?: (column: string) => void;
  onRetry?: () => void;
  onPrev?: () => void;
  onNext?: () => void;
  /** Custom empty placeholder. */
  empty?: ReactNode;
}

const fieldOf = (row: unknown, key: string): unknown =>
  (row as Record<string, unknown>)[key];

const renderValue = (value: unknown): ReactNode => {
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean')
    return value.toString();
  if (value !== null && typeof value === 'object') return JSON.stringify(value);
  return '';
};

/**
 * AdminDataTable — the shared table for every admin list. Wraps shadcn `Table`
 * with sortable headers, per-column `cell` renderers and a controlled
 * pagination footer, all behind `AdminStateBlock` (loading → error → empty →
 * data). Designed to pair with `useAdminList`.
 *
 * Below `md` (phones, Telegram) each row renders as a card instead: the first
 * column is the card title, the rest are label/value pairs, and sorting moves
 * to a compact Select + direction toggle. Both layouts use the same `cell`
 * renderers; the switch is CSS only.
 *
 * Port of template-vue's `AdminDataTable.vue`.
 * TODO: extract to core/frontend-react when a second React app needs this.
 */
export function AdminDataTable<T>({
  columns,
  rows,
  rowKey,
  isLoading = false,
  error,
  sortBy = null,
  sortDir = 'desc',
  page = 1,
  totalPages = 1,
  total,
  dense = false,
  hidePagination = false,
  onRowClick,
  onSort,
  onRetry,
  onPrev,
  onNext,
  empty,
}: AdminDataTableProps<T>) {
  const t = useTranslations('admin');

  const isEmpty = !isLoading && !error && rows.length === 0;
  const clickableRows = !!onRowClick;

  const sortableColumns = columns.filter((c) => c.sortable);
  const titleColumn = columns[0];
  const fieldColumns = columns.slice(1).filter((c) => c.label);
  const actionColumns = columns.slice(1).filter((c) => !c.label);

  // Default to an `id` field when no rowKey is given, else the index.
  const resolveRowKey = (row: T, index: number): string | number => {
    if (rowKey) return rowKey(row);
    const id = fieldOf(row, 'id');
    return typeof id === 'string' || typeof id === 'number' ? id : index;
  };

  const renderCell = (column: AdminColumn<T>, row: T): ReactNode =>
    column.cell ? column.cell(row) : renderValue(fieldOf(row, column.key));

  // Clicks on links/buttons/menus inside a row keep their own behaviour.
  const handleRowClick = (row: T, event: MouseEvent) => {
    if (!onRowClick) return;
    const target = event.target as HTMLElement | null;
    if (target?.closest('a, button, [role="menuitem"], input')) return;
    onRowClick(row);
  };

  // Mobile sort control. `setSort` in useAdminList toggles the direction when
  // the same column comes in again, so both controls just report `onSort`.
  const onMobileSort = (value: string) => {
    if (value && value !== sortBy) onSort?.(value);
  };
  const toggleDir = () => {
    if (sortBy) onSort?.(sortBy);
  };

  return (
    <div>
      <AdminStateBlock
        isLoading={isLoading}
        error={error}
        isEmpty={isEmpty}
        empty={empty}
        onRetry={onRetry}
      >
        {/* Phones: sort control + one card per row */}
        <div className="flex flex-col gap-2 md:hidden">
          {sortableColumns.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground shrink-0 text-xs">
                {t('table.sortBy')}
              </span>
              <Select value={sortBy ?? ''} onValueChange={onMobileSort}>
                <SelectTrigger size="sm" className="min-w-0 flex-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {sortableColumns.map((column) => (
                    <SelectItem key={column.key} value={column.key}>
                      {column.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                size="icon-sm"
                variant="outline"
                disabled={!sortBy}
                aria-label={t('table.sortDir')}
                onClick={toggleDir}
              >
                {sortDir === 'asc' ? (
                  <ArrowUp className="h-4 w-4" />
                ) : (
                  <ArrowDown className="h-4 w-4" />
                )}
              </Button>
            </div>
          )}

          <ul className="flex flex-col gap-2">
            {rows.map((row, index) => (
              <li
                key={resolveRowKey(row, index)}
                className={cn(
                  'border-border bg-card rounded-xl border p-3 text-sm',
                  clickableRows &&
                    'active:bg-muted/50 cursor-pointer transition-colors'
                )}
                onClick={(e) => {
                  handleRowClick(row, e);
                }}
              >
                <div className="mb-2 flex items-start justify-between gap-2">
                  {titleColumn && (
                    <div className="min-w-0 py-0.5 font-medium break-words">
                      {renderCell(titleColumn, row)}
                    </div>
                  )}
                  {actionColumns.map((column) => (
                    <div
                      key={column.key}
                      className="-my-1 -mr-1 shrink-0 empty:hidden"
                    >
                      {renderCell(column, row)}
                    </div>
                  ))}
                </div>
                <dl className="grid grid-cols-[minmax(0,auto)_minmax(0,1fr)] gap-x-3 gap-y-1.5">
                  {fieldColumns.map((column) => (
                    <Fragment key={column.key}>
                      <dt className="text-muted-foreground text-xs leading-5">
                        {column.label}
                      </dt>
                      <dd className="min-w-0 break-words">
                        {renderCell(column, row)}
                      </dd>
                    </Fragment>
                  ))}
                </dl>
              </li>
            ))}
          </ul>
        </div>

        {/* md and up: the table */}
        <div className="border-border hidden overflow-x-auto rounded-xl border md:block">
          <Table className={cn(dense && 'text-xs')}>
            <TableHeader>
              <TableRow>
                {columns.map((column) => (
                  <TableHead
                    key={column.key}
                    className={cn(
                      column.sortable && 'cursor-pointer select-none',
                      dense && 'h-8 px-1.5',
                      column.className
                    )}
                    title={column.hint}
                    onClick={() => {
                      if (column.sortable) onSort?.(column.key);
                    }}
                  >
                    <span className="inline-flex items-center gap-1">
                      <span
                        className={cn(
                          column.hint &&
                            'underline decoration-dotted underline-offset-4'
                        )}
                      >
                        {column.label}
                      </span>
                      {column.sortable &&
                        (sortBy === column.key && sortDir === 'asc' ? (
                          <ArrowUp className="h-3.5 w-3.5" />
                        ) : sortBy === column.key && sortDir === 'desc' ? (
                          <ArrowDown className="h-3.5 w-3.5" />
                        ) : (
                          <ChevronsUpDown className="text-muted-foreground/50 h-3.5 w-3.5" />
                        ))}
                    </span>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row, index) => (
                <TableRow
                  key={resolveRowKey(row, index)}
                  className={cn(clickableRows && 'cursor-pointer')}
                  onClick={(e) => {
                    handleRowClick(row, e);
                  }}
                >
                  {columns.map((column) => (
                    <TableCell
                      key={column.key}
                      className={cn(dense && 'px-1.5 py-1.5', column.className)}
                    >
                      {renderCell(column, row)}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {!hidePagination && (
          <AdminPagination
            page={page}
            totalPages={totalPages}
            total={total}
            onPrev={() => onPrev?.()}
            onNext={() => onNext?.()}
          />
        )}
      </AdminStateBlock>
    </div>
  );
}
