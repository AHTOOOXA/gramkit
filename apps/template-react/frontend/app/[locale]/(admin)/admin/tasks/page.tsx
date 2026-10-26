'use client';

import { Info } from 'lucide-react';
import { useTranslations } from 'next-intl';

import {
  AdminEmptyState,
  AdminStateBlock,
} from '@/components/admin/AdminStateBlock';
import { AdminTaskCard } from '@/components/admin/tasks/AdminTaskCard';
import { Skeleton } from '@/components/ui/skeleton';
import { useAuth } from '@/hooks';
import { useListTasksAdminTasksGet } from '@/src/gen/hooks/useListTasksAdminTasksGet';

/**
 * Admin → Tasks — the maintenance tasks registered with `@admin_task` on the
 * backend (`app/services/admin_tasks.py`, framework in core), one
 * AdminTaskCard each. Tasks run inside the live server, in the request's
 * transaction, and every run is audit-logged as `admin_task:<name>`.
 *
 * Any admin sees the list; only the owner gets the run controls (the backend
 * answers 403 to anyone else either way).
 *
 * Port of template-vue's `AdminTasks.vue`.
 */
export default function AdminTasksPage() {
  const t = useTranslations('admin');
  const { isAdminOrOwner, isOwner } = useAuth();

  const { data, isLoading, error, refetch } = useListTasksAdminTasksGet({
    query: { enabled: isAdminOrOwner, staleTime: 5 * 60 * 1000 },
  });

  const tasks = data ?? [];

  return (
    <div className="flex flex-col gap-4">
      <p className="text-muted-foreground text-sm">{t('tasks.description')}</p>

      {!isOwner && (
        <p className="text-muted-foreground flex items-start gap-1.5 text-xs">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          {t('tasks.ownerOnly')}
        </p>
      )}

      <AdminStateBlock
        isLoading={isLoading}
        error={error}
        isEmpty={!tasks.length}
        onRetry={() => void refetch()}
        loading={
          <div className="flex flex-col gap-3">
            {[1, 2].map((i) => (
              <Skeleton key={i} className="h-32 w-full rounded-xl" />
            ))}
          </div>
        }
        empty={<AdminEmptyState>{t('tasks.empty')}</AdminEmptyState>}
      >
        <div className="flex flex-col gap-3">
          {tasks.map((task) => (
            <AdminTaskCard key={task.name} task={task} canRun={isOwner} />
          ))}
        </div>
      </AdminStateBlock>
    </div>
  );
}
