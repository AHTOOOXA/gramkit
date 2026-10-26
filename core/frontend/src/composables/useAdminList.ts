import { computed, ref, type ComputedRef, type Ref } from 'vue';

export type AdminSortDir = 'asc' | 'desc';

/**
 * Shape of the filter bag emitted by `AdminFilterBar` (search + date range).
 * Section-specific filters (e.g. an `action` select) are layered on via
 * `setFilters` and surfaced through `extraParams`.
 */
export interface AdminListFilters {
  search?: string;
  date_from?: string;
  date_to?: string;
  [key: string]: string | number | null | undefined;
}

/**
 * The query-params object handed to a generated kubb list hook. It mirrors the
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
}

/**
 * useAdminList — reactive list controls (pagination / sort / filters) that
 * compute into the `AdminListParams` query object every admin list endpoint
 * accepts. Reusable across any admin list screen (audit log, users, ...).
 *
 * Server state stays in TanStack Query — this only owns the *request inputs*.
 *
 * @example
 * const list = useAdminList({ sortBy: 'created_at' });
 * const { data } = useListAuditLogAdminAuditLogGet(list.params);
 */
export function useAdminList(options: UseAdminListOptions = {}): {
  page: Ref<number>;
  pageSize: Ref<number>;
  sortBy: Ref<string | null>;
  sortDir: Ref<AdminSortDir>;
  filters: Ref<AdminListFilters>;
  params: ComputedRef<AdminListParams>;
  nextPage: () => void;
  prevPage: () => void;
  setPage: (value: number) => void;
  setSort: (column: string) => void;
  setFilters: (next: AdminListFilters) => void;
  reset: () => void;
} {
  const page = ref(1);
  const pageSize = ref(options.pageSize ?? 25);
  const sortBy = ref<string | null>(options.sortBy ?? null);
  const sortDir = ref<AdminSortDir>(options.sortDir ?? 'desc');
  const filters = ref<AdminListFilters>({});

  const params = computed<AdminListParams>(() => {
    const cleaned: AdminListFilters = {};
    for (const [key, value] of Object.entries(filters.value)) {
      // Drop empty strings so the backend treats absent filters as "no filter".
      if (value === '' || value === null || value === undefined) continue;
      cleaned[key] = value;
    }
    return {
      page: page.value,
      page_size: pageSize.value,
      sort_by: sortBy.value,
      sort_dir: sortDir.value,
      ...cleaned,
    };
  });

  const setPage = (value: number) => {
    page.value = Math.max(1, value);
  };

  const nextPage = () => setPage(page.value + 1);
  const prevPage = () => setPage(page.value - 1);

  const setSort = (column: string) => {
    if (sortBy.value === column) {
      sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc';
    } else {
      sortBy.value = column;
      sortDir.value = 'asc';
    }
    // Any sort change resets to the first page.
    page.value = 1;
  };

  const setFilters = (next: AdminListFilters) => {
    filters.value = { ...next };
    // Filter changes invalidate the current page window.
    page.value = 1;
  };

  const reset = () => {
    page.value = 1;
    pageSize.value = options.pageSize ?? 25;
    sortBy.value = options.sortBy ?? null;
    sortDir.value = options.sortDir ?? 'desc';
    filters.value = {};
  };

  return {
    page,
    pageSize,
    sortBy,
    sortDir,
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
