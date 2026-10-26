'use client';

import {
  AdminDataTable,
  type AdminDataTableProps,
} from '@/components/admin/AdminDataTable';

/**
 * AdminUserSubTable — a labelled wrapper around AdminDataTable for the
 * per-user sub-lists on the detail page (payments / subscriptions / whatever
 * an app panel lists). The parent owns the query (via useAdminList + a
 * generated hook) and passes rows + pagination state down; this just frames
 * it. Custom cells go through the columns' `cell` renderers.
 *
 * Port of template-vue's `AdminUserSubTable.vue`.
 * TODO: extract to core/frontend-react when a second React app needs this.
 */
export function AdminUserSubTable<T>({
  title,
  ...tableProps
}: AdminDataTableProps<T> & {
  /** Optional heading; the detail page's tab label usually names the list already. */
  title?: string;
}) {
  return (
    <section className="flex flex-col gap-2">
      {title && <h3 className="text-sm font-semibold">{title}</h3>}
      <AdminDataTable {...tableProps} />
    </section>
  );
}
