import { useCallback, useMemo, useState } from 'react';

export type AdminSortDir = 'asc' | 'desc';

/**
 * Shape of the filter bag emitted by `AdminFilterBar` (search + date range).
 * Section-specific filters (e.g. an `action` select) are layered on via
 * `setFilters` and end up in `params`.
 */
export interface AdminListFilters {
  search?: string;
  date_from?: string;
  date_to?: string;
  [key: string]: string | number | null | undefined;
}

/**
 * The query-params object handed to a generated Kubb list hook. It mirrors the
 * common `AdminListParams` envelope (page / page_size / sort / search / date
 * range) plus any whitelisted section filters.
 */
export interface AdminListParams extends AdminListFilters {
  page: number;
  page_size: number;
  sort_by?: string | null;
  sort_dir?: AdminSortDir;
}

export interface UseAdminListOptions {
  pageSize?: number;
  sortBy?: string | null;
  sortDir?: AdminSortDir;
  /** Filters for the first request (e.g. seeded from the URL). */
  initialFilters?: AdminListFilters;
}

export interface AdminList {
  page: number;
  pageSize: number;
  sortBy: string | null;
  sortDir: AdminSortDir;
  filters: AdminListFilters;
  params: AdminListParams;
  nextPage: () => void;
  prevPage: () => void;
  setPage: (value: number) => void;
  setSort: (column: string) => void;
  setFilters: (next: AdminListFilters) => void;
  reset: () => void;
}

/**
 * useAdminList — list controls (pagination / sort / filters) that compute into
 * the `AdminListParams` query object every admin list endpoint accepts.
 * Reusable across any admin list screen (audit log, users, ...).
 *
 * Server state stays in TanStack Query — this only owns the *request inputs*.
 * Same rules as the Vue `useAdminList` (core/frontend): empty filter values are
 * dropped, any sort or filter change resets to page 1, sorting the same column
 * again toggles the direction, and a new column starts ascending.
 *
 * TODO: extract to core/frontend-react when a second React app needs this.
 *
 * @example
 * const list = useAdminList({ sortBy: 'created_at' });
 * const { data } = useListAuditLogAdminAuditLogGet(list.params);
 */
export function useAdminList(options: UseAdminListOptions = {}): AdminList {
  const defaultPageSize = options.pageSize ?? 25;
  const defaultSortBy = options.sortBy ?? null;
  const defaultSortDir = options.sortDir ?? 'desc';

  const [page, setPageState] = useState(1);
  const [pageSize, setPageSize] = useState(defaultPageSize);
  // One state for column + direction, so a toggle is a single pure update.
  const [sort, setSortState] = useState<{
    by: string | null;
    dir: AdminSortDir;
  }>({ by: defaultSortBy, dir: defaultSortDir });
  const [filters, setFiltersState] = useState<AdminListFilters>(
    () => options.initialFilters ?? {}
  );

  const params = useMemo<AdminListParams>(() => {
    const cleaned: AdminListFilters = {};
    for (const [key, value] of Object.entries(filters)) {
      // Drop empty strings so the backend treats absent filters as "no filter".
      if (value === '' || value === null || value === undefined) continue;
      cleaned[key] = value;
    }
    return {
      page,
      page_size: pageSize,
      sort_by: sort.by,
      sort_dir: sort.dir,
      ...cleaned,
    };
  }, [filters, page, pageSize, sort]);

  const setPage = useCallback((value: number) => {
    setPageState(Math.max(1, value));
  }, []);

  const nextPage = useCallback(() => {
    setPageState((p) => p + 1);
  }, []);

  const prevPage = useCallback(() => {
    setPageState((p) => Math.max(1, p - 1));
  }, []);

  const setSort = useCallback((column: string) => {
    setSortState((prev) =>
      prev.by === column
        ? { by: prev.by, dir: prev.dir === 'asc' ? 'desc' : 'asc' }
        : { by: column, dir: 'asc' }
    );
    // Any sort change resets to the first page.
    setPageState(1);
  }, []);

  const setFilters = useCallback((next: AdminListFilters) => {
    setFiltersState({ ...next });
    // Filter changes invalidate the current page window.
    setPageState(1);
  }, []);

  const reset = useCallback(() => {
    setPageState(1);
    setPageSize(defaultPageSize);
    setSortState({ by: defaultSortBy, dir: defaultSortDir });
    setFiltersState({});
  }, [defaultPageSize, defaultSortBy, defaultSortDir]);

  return {
    page,
    pageSize,
    sortBy: sort.by,
    sortDir: sort.dir,
    filters,
    params,
    nextPage,
    prevPage,
    setPage,
    setSort,
    setFilters,
    reset,
  };
}
