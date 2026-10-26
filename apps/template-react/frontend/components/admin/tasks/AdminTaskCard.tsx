'use client';

import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { getErrorMessage } from '@tma-platform/core-react/errors';
import { FlaskConical, History, Loader2, Play } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { toast } from 'sonner';

import { AdminActionDialog } from '@/components/admin/AdminActionDialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Link } from '@/i18n/navigation';
import { listAuditActionsAdminAuditLogActionsGetQueryKey } from '@/src/gen/hooks/useListAuditActionsAdminAuditLogActionsGet';
import { listAuditLogAdminAuditLogGetQueryKey } from '@/src/gen/hooks/useListAuditLogAdminAuditLogGet';
import { useRunTaskAdminTasksNamePost } from '@/src/gen/hooks/useRunTaskAdminTasksNamePost';
import type { AdminTaskInfo } from '@/src/gen/models/AdminTaskInfo';

interface RunOutcome {
  dryRun: boolean;
  result: Record<string, unknown>;
  at: Date;
}

/**
 * AdminTaskCard — one registered admin task (`@admin_task` on the backend):
 * name, description, a "changes data" badge, the run controls, the last
 * result and a link to the task's runs in the audit log.
 *
 * - Destructive task: **Dry run**, then **Apply**. Apply stays disabled until
 *   a dry run succeeded in this view, and asks for confirmation in
 *   AdminActionDialog (it stays open with a spinner and closes on success; on
 *   an error it stays open for a retry). After an apply, the next apply needs
 *   a fresh dry run.
 * - Read-only task: a single **Run**. It sends `dry_run: true`: a read-only
 *   task ignores the flag, and a mutating task someone forgot to mark
 *   `destructive` then stays a harmless dry run instead of a one-click apply.
 *
 * Run controls only render when `canRun` (the owner); the backend enforces
 * owner-only either way. Every run writes an `admin_task:<name>` audit row, so
 * a successful run invalidates the cached audit-log list and action options.
 *
 * Port of template-vue's `AdminTaskCard.vue`.
 * TODO: extract to core/frontend-react when a second React app needs this.
 */
export function AdminTaskCard({
  task,
  canRun,
}: {
  task: AdminTaskInfo;
  canRun: boolean;
}) {
  const t = useTranslations('admin');
  const queryClient = useQueryClient();
  const runTask = useRunTaskAdminTasksNamePost();

  const [lastRun, setLastRun] = useState<RunOutcome | null>(null);
  const [dryRunPassed, setDryRunPassed] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  // Which control started the pending run, so only that one shows a spinner.
  const [pendingMode, setPendingMode] = useState<'dry' | 'apply' | null>(null);

  const historyAction = `admin_task:${task.name}`;

  const resultTitle = !lastRun
    ? ''
    : !task.destructive
      ? t('tasks.resultRun')
      : lastRun.dryRun
        ? t('tasks.resultDry')
        : t('tasks.resultApplied');

  /** Run the task; resolves to whether it succeeded (errors are toasted here). */
  const execute = async (dryRun: boolean): Promise<boolean> => {
    setPendingMode(dryRun ? 'dry' : 'apply');
    try {
      const res = await runTask.mutateAsync({
        name: task.name,
        data: { dry_run: dryRun },
      });
      setLastRun({ dryRun: res.dry_run, result: res.result, at: new Date() });
      setDryRunPassed(res.dry_run);
      void queryClient.invalidateQueries({
        queryKey: listAuditLogAdminAuditLogGetQueryKey(),
      });
      void queryClient.invalidateQueries({
        queryKey: listAuditActionsAdminAuditLogActionsGetQueryKey(),
      });
      return true;
    } catch (e) {
      if (dryRun) setDryRunPassed(false);
      toast.error(getErrorMessage(e));
      return false;
    } finally {
      setPendingMode(null);
    }
  };

  // Read-only task: still a dry run (see the component docs above).
  const onDryRun = () => void execute(true);

  const onConfirmApply = async () => {
    if (await execute(false)) setConfirmOpen(false);
  };

  return (
    <section className="bg-card flex flex-col gap-3 rounded-xl border p-4">
      <div className="flex flex-col gap-1.5">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="font-mono text-[15px] font-semibold break-all">
            {task.name}
          </h2>
          {task.destructive && (
            <Badge variant="destructive">{t('tasks.destructive')}</Badge>
          )}
        </div>
        <p className="text-muted-foreground text-sm">{task.description}</p>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
        {canRun &&
          (task.destructive ? (
            <>
              <Button
                variant="outline"
                disabled={runTask.isPending}
                onClick={onDryRun}
              >
                {pendingMode === 'dry' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <FlaskConical className="h-4 w-4" />
                )}
                {pendingMode === 'dry' ? t('tasks.running') : t('tasks.dryRun')}
              </Button>
              <Button
                variant="destructive"
                disabled={!dryRunPassed || runTask.isPending}
                title={dryRunPassed ? undefined : t('tasks.dryRunFirst')}
                onClick={() => {
                  setConfirmOpen(true);
                }}
              >
                <Play className="h-4 w-4" />
                {t('tasks.apply')}
              </Button>
              {!dryRunPassed && (
                <span className="text-muted-foreground text-xs">
                  {t('tasks.dryRunFirst')}
                </span>
              )}
            </>
          ) : (
            <Button disabled={runTask.isPending} onClick={onDryRun}>
              {pendingMode ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              {pendingMode ? t('tasks.running') : t('tasks.run')}
            </Button>
          ))}

        <Button asChild variant="ghost" size="sm" className="w-fit sm:ml-auto">
          <Link
            href={{
              pathname: '/admin/audit-log',
              query: { action: historyAction },
            }}
          >
            <History className="h-4 w-4" />
            {t('tasks.history')}
          </Link>
        </Button>
      </div>

      {lastRun && (
        <div className="flex flex-col gap-1.5 border-t pt-3">
          <p className="flex flex-wrap items-baseline gap-x-2 text-sm font-medium">
            {resultTitle}
            <span className="text-muted-foreground text-xs font-normal tabular-nums">
              {lastRun.at.toLocaleTimeString()}
            </span>
          </p>
          <pre className="bg-muted max-h-80 overflow-auto rounded-lg p-3 font-mono text-xs leading-relaxed break-all whitespace-pre-wrap">
            {JSON.stringify(lastRun.result, null, 2)}
          </pre>
        </div>
      )}

      <AdminActionDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t('tasks.applyConfirmTitle', { name: task.name })}
        description={t('tasks.applyConfirmDesc')}
        confirmLabel={t('tasks.apply')}
        pending={pendingMode === 'apply'}
        onConfirm={() => void onConfirmApply()}
      />
    </section>
  );
}
