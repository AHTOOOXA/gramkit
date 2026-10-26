'use client';

import { useTranslations } from 'next-intl';

import { formatDate, roleVariant, userLabel } from '@/lib/admin/format';
import { useAdminLabels } from '@/hooks/useAdminLabels';
import { useAdminList } from '@/hooks/useAdminList';
import {
  AdminDataTable,
  type AdminColumn,
} from '@/components/admin/AdminDataTable';
import { AdminFilterBar } from '@/components/admin/AdminFilterBar';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useAuth } from '@/hooks';
import { Link, useRouter } from '@/i18n/navigation';
import { useListUsersAdminUsersGet } from '@/src/gen/hooks/useListUsersAdminUsersGet';
import type { AdminUserListItem } from '@/src/gen/models/AdminUserListItem';

/**
 * Admin → Users — searchable/filterable user list. Built on the shared admin
 * stack (AdminFilterBar → useAdminList → the generated `list_users` hook →
 * AdminDataTable). A row (a card on phones) opens the per-user detail page.
 *
 * Port of template-vue's `AdminUsers.vue`.
 */
export default function AdminUsersPage() {
  const t = useTranslations('admin');
  const router = useRouter();
  const { isAdminOrOwner } = useAuth();
  const { roleLabel, userTypeLabel } = useAdminLabels();

  const list = useAdminList({ sortBy: 'created_at', sortDir: 'desc' });

  const { data, isLoading, error, refetch } = useListUsersAdminUsersGet(
    list.params,
    { query: { enabled: isAdminOrOwner, staleTime: 30 * 1000 } }
  );

  const rows = data?.items ?? [];

  const columns: AdminColumn<AdminUserListItem>[] = [
    {
      key: 'username',
      label: t('users.columns.user'),
      sortable: true,
      cell: (row) => (
        <>
          <Link
            href={`/admin/users/${row.id}`}
            className="font-medium hover:underline"
          >
            {userLabel(row)}
          </Link>
          {row.user_type === 'GUEST' && (
            <span className="text-muted-foreground ml-1.5 text-xs font-normal">
              {userTypeLabel(row.user_type)}
            </span>
          )}
        </>
      ),
    },
    {
      key: 'role',
      label: t('users.columns.role'),
      sortable: true,
      cell: (row) => (
        <Badge variant={roleVariant(row.role)}>{roleLabel(row.role)}</Badge>
      ),
    },
    {
      key: 'telegram_id',
      label: t('users.columns.telegram'),
      cell: (row) => (
        <span className="text-muted-foreground text-xs tabular-nums">
          {row.telegram_id ?? '—'}
        </span>
      ),
    },
    {
      key: 'created_at',
      label: t('users.columns.joined'),
      sortable: true,
      cell: (row) => (
        <span className="text-muted-foreground whitespace-nowrap">
          {formatDate(row.created_at)}
        </span>
      ),
    },
  ];

  // Selects can't hold `undefined`, so 'all' stands for "no filter".
  const roleFilter = (list.filters.role as string | undefined) ?? 'all';
  const typeFilter = (list.filters.user_type as string | undefined) ?? 'all';

  return (
    <div className="flex flex-col gap-4">
      <p className="text-muted-foreground text-sm">{t('users.description')}</p>

      <AdminFilterBar filters={list.filters} onFiltersChange={list.setFilters}>
        <div className="grid w-full grid-cols-2 gap-3 sm:flex sm:w-auto">
          <div className="flex min-w-0 flex-col gap-1">
            <Label
              htmlFor="admin-users-role"
              className="text-muted-foreground text-xs"
            >
              {t('users.roleFilter')}
            </Label>
            <Select
              value={roleFilter}
              onValueChange={(value) => {
                list.setFilters({
                  ...list.filters,
                  role: value === 'all' ? undefined : value,
                });
              }}
            >
              <SelectTrigger id="admin-users-role" className="w-full sm:w-36">
                <SelectValue placeholder={t('users.allRoles')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('users.allRoles')}</SelectItem>
                <SelectItem value="user">{t('users.role.user')}</SelectItem>
                <SelectItem value="admin">{t('users.role.admin')}</SelectItem>
                <SelectItem value="owner">{t('users.role.owner')}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex min-w-0 flex-col gap-1">
            <Label
              htmlFor="admin-users-type"
              className="text-muted-foreground text-xs"
            >
              {t('users.typeFilter')}
            </Label>
            <Select
              value={typeFilter}
              onValueChange={(value) => {
                list.setFilters({
                  ...list.filters,
                  user_type: value === 'all' ? undefined : value,
                });
              }}
            >
              <SelectTrigger id="admin-users-type" className="w-full sm:w-36">
                <SelectValue placeholder={t('users.allTypes')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('users.allTypes')}</SelectItem>
                <SelectItem value="REGISTERED">
                  {t('users.type.registered')}
                </SelectItem>
                <SelectItem value="GUEST">{t('users.type.guest')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
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
        onRowClick={(row) => {
          router.push(`/admin/users/${row.id}`);
        }}
      />
    </div>
  );
}
