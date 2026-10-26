'use client';

import { useSearchParams } from 'next/navigation';
import { Download } from 'lucide-react';
import { useTranslations } from 'next-intl';

import { exportCsv } from '@/lib/admin/csv';
import { formatDate } from '@/lib/admin/format';
import { useAdminLabels } from '@/hooks/useAdminLabels';
import { useAdminList } from '@/hooks/useAdminList';
import {
  AdminDataTable,
  type AdminColumn,
} from '@/components/admin/AdminDataTable';
import { AdminFilterBar } from '@/components/admin/AdminFilterBar';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useAuth } from '@/hooks';
import { useListAuditActionsAdminAuditLogActionsGet } from '@/src/gen/hooks/useListAuditActionsAdminAuditLogActionsGet';
import { useListAuditLogAdminAuditLogGet } from '@/src/gen/hooks/useListAuditLogAdminAuditLogGet';
import type { AuditLogSchema } from '@/src/gen/models/AuditLogSchema';

const actorLabel = (row: AuditLogSchema): string =>
  row.actor_username ??
  (row.actor_telegram_id ? `#${String(row.actor_telegram_id)}` : '—');

const targetLabel = (row: AuditLogSchema): string => {
  if (!row.target_type && !row.target_id) return '—';
  return [row.target_type, row.target_id].filter(Boolean).join(':');
};

const detailLabel = (row: AuditLogSchema): string =>
  row.detail ? JSON.stringify(row.detail) : '—';

/**
 * Admin → Audit log — the trail of mutating admin/owner actions:
 * AdminFilterBar (search + action filter + date range) → useAdminList → the
 * generated `list_audit_log` hook → AdminDataTable, with CSV export of the
 * current page. The action Select lists every action recorded so far
 * (`/admin/audit-log/actions`). Empty until something writes audit rows; the
 * empty state is expected. `?action=<action>` pre-selects the action filter
 * (the Tasks section's "Run history" link uses it); the filters aren't synced
 * back to the URL.
 *
 * Port of template-vue's `AdminAuditLog.vue`.
 */
export default function AdminAuditLogPage() {
  const t = useTranslations('admin');
  const { isAdminOrOwner } = useAuth();
  const { roleLabel } = useAdminLabels();

  // Seed the action filter once from the URL, before the first fetch.
  const initialAction = useSearchParams().get('action');
  const list = useAdminList({
    sortBy: 'created_at',
    sortDir: 'desc',
    initialFilters: initialAction ? { action: initialAction } : {},
  });

  const { data, isLoading, error, refetch } = useListAuditLogAdminAuditLogGet(
    list.params,
    { query: { enabled: isAdminOrOwner, staleTime: 30 * 1000 } }
  );

  const { data: actions } = useListAuditActionsAdminAuditLogActionsGet({
    query: { enabled: isAdminOrOwner, staleTime: 5 * 60 * 1000 },
  });

  // The seeded `?action=` may not be recorded yet (a task nobody has run), so
  // it isn't in `/actions`; keep it selectable so the Select shows the filter.
  const currentAction = list.filters.action as string | undefined;
  const known = actions ?? [];
  const actionOptions =
    currentAction && !known.includes(currentAction)
      ? [currentAction, ...known]
      : known;

  const rows = data?.items ?? [];

  const columns: AdminColumn<AuditLogSchema>[] = [
    {
      key: 'action',
      label: t('auditLog.columns.action'),
      sortable: true,
      cell: (row) => (
        <span className="font-mono text-[13px] font-medium">{row.action}</span>
      ),
    },
    {
      key: 'actor',
      label: t('auditLog.columns.actor'),
      cell: (row) => (
        <>
          <span>{actorLabel(row)}</span>
          <span className="text-muted-foreground ml-1 text-xs">
            ({roleLabel(row.actor_role)})
          </span>
        </>
      ),
    },
    {
      key: 'target',
      label: t('auditLog.columns.target'),
      cell: (row) => <span className="break-all">{targetLabel(row)}</span>,
    },
    {
      key: 'created_at',
      label: t('auditLog.columns.date'),
      sortable: true,
      cell: (row) => (
        <span className="text-muted-foreground whitespace-nowrap">
          {formatDate(row.created_at, true)}
        </span>
      ),
    },
    {
      key: 'detail',
      label: t('auditLog.columns.detail'),
      cell: (row) => (
        <span
          className="text-muted-foreground line-clamp-2 font-mono text-xs break-all md:line-clamp-1 md:max-w-[18rem]"
          title={detailLabel(row)}
        >
          {detailLabel(row)}
        </span>
      ),
    },
  ];

  const onExport = () => {
    exportCsv(
      rows,
      [
        { header: t('auditLog.columns.action'), accessor: (r) => r.action },
        { header: t('auditLog.columns.actor'), accessor: (r) => actorLabel(r) },
        { header: t('users.columns.role'), accessor: (r) => r.actor_role },
        {
          header: t('auditLog.columns.target'),
          accessor: (r) => targetLabel(r),
        },
        { header: t('auditLog.columns.date'), accessor: (r) => r.created_at },
        { header: t('auditLog.columns.detail'), accessor: (r) => r.detail },
      ],
      'audit-log'
    );
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-muted-foreground text-sm">
          {t('auditLog.description')}
        </p>
        <Button
          size="sm"
          variant="outline"
          className="w-fit shrink-0"
          disabled={!rows.length}
          onClick={onExport}
        >
          <Download className="h-4 w-4" />
          {t('table.exportCsv')}
        </Button>
      </div>

      <AdminFilterBar filters={list.filters} onFiltersChange={list.setFilters}>
        <div className="flex w-full min-w-0 flex-col gap-1 sm:w-auto">
          <Label
            htmlFor="admin-audit-action"
            className="text-muted-foreground text-xs"
          >
            {t('auditLog.actionFilter')}
          </Label>
          <Select
            value={currentAction ?? 'all'}
            onValueChange={(value) => {
              list.setFilters({
                ...list.filters,
                action: value === 'all' ? undefined : value,
              });
            }}
          >
            <SelectTrigger id="admin-audit-action" className="w-full sm:w-48">
              <SelectValue placeholder={t('auditLog.allActions')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('auditLog.allActions')}</SelectItem>
              {actionOptions.map((action) => (
                <SelectItem key={action} value={action}>
                  {action}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </AdminFilterBar>

      <AdminDataTable
        columns={columns}
        rows={rows}
        isLoading={isLoading}
        error={error}
        sortBy={list.sortBy}
        sortDir={list.sortDir}
        page={list.page}
        totalPages={data?.total_pages ?? 1}
        total={data?.total ?? 0}
        onSort={list.setSort}
        onRetry={() => void refetch()}
        onPrev={list.prevPage}
        onNext={list.nextPage}
      />
    </div>
  );
}
