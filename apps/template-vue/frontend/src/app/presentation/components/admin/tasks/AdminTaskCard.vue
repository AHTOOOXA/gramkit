<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useQueryClient } from '@tanstack/vue-query';
import { toast } from 'vue-sonner';
import { FlaskConical, History, Loader2, Play } from '@lucide/vue';
import { getErrorMessage } from '@core/errors';
import type { AdminTaskInfo } from '@gen/models/AdminTaskInfo';
import { useRunTaskAdminTasksNamePost } from '@gen/hooks/useRunTaskAdminTasksNamePost';
import { listAuditLogAdminAuditLogGetQueryKey } from '@gen/hooks/useListAuditLogAdminAuditLogGet';
import { listAuditActionsAdminAuditLogActionsGetQueryKey } from '@gen/hooks/useListAuditActionsAdminAuditLogActionsGet';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import AdminActionDialog from '@app/presentation/components/admin/AdminActionDialog.vue';

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
 * TODO: extract to core when a third Vue app needs this (each Vue app keeps
 * its own copy for now, built on its own `ui/*` kit).
 */
const props = defineProps<{ task: AdminTaskInfo; canRun: boolean }>();

const { t } = useI18n();
const queryClient = useQueryClient();
const runTask = useRunTaskAdminTasksNamePost();

interface RunOutcome {
  dryRun: boolean;
  result: Record<string, unknown>;
  at: Date;
}

const lastRun = ref<RunOutcome | null>(null);
const dryRunPassed = ref(false);
const confirmOpen = ref(false);
// Which control started the pending run, so only that one shows a spinner.
const pendingMode = ref<'dry' | 'apply' | null>(null);

const historyAction = computed(() => `admin_task:${props.task.name}`);

const resultTitle = computed(() => {
  if (!lastRun.value) return '';
  if (!props.task.destructive) return t('admin.tasks.resultRun');
  return lastRun.value.dryRun ? t('admin.tasks.resultDry') : t('admin.tasks.resultApplied');
});

const resultJson = computed(() =>
  lastRun.value ? JSON.stringify(lastRun.value.result, null, 2) : '',
);

/** Run the task; resolves to whether it succeeded (errors are toasted here). */
const execute = async (dryRun: boolean): Promise<boolean> => {
  pendingMode.value = dryRun ? 'dry' : 'apply';
  try {
    const res = await runTask.mutateAsync({ name: props.task.name, data: { dry_run: dryRun } });
    lastRun.value = { dryRun: res.dry_run, result: res.result, at: new Date() };
    dryRunPassed.value = res.dry_run;
    void queryClient.invalidateQueries({ queryKey: listAuditLogAdminAuditLogGetQueryKey() });
    void queryClient.invalidateQueries({
      queryKey: listAuditActionsAdminAuditLogActionsGetQueryKey(),
    });
    return true;
  } catch (e) {
    if (dryRun) dryRunPassed.value = false;
    toast.error(getErrorMessage(e));
    return false;
  } finally {
    pendingMode.value = null;
  }
};

const onDryRun = () => void execute(true);

// Read-only task: still a dry run (see the component docs above).
const onRun = () => void execute(true);

const onConfirmApply = async () => {
  if (await execute(false)) confirmOpen.value = false;
};
</script>

<template>
  <section class="flex flex-col gap-3 rounded-xl border bg-card p-4">
    <div class="flex flex-col gap-1.5">
      <div class="flex flex-wrap items-center gap-2">
        <h2 class="break-all font-mono text-[15px] font-semibold">{{ task.name }}</h2>
        <Badge
          v-if="task.destructive"
          variant="destructive"
        >
          {{ t('admin.tasks.destructive') }}
        </Badge>
      </div>
      <p class="text-sm text-muted-foreground">{{ task.description }}</p>
    </div>

    <div class="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
      <template v-if="canRun">
        <template v-if="task.destructive">
          <Button
            variant="outline"
            :disabled="runTask.isPending.value"
            @click="onDryRun"
          >
            <Loader2
              v-if="pendingMode === 'dry'"
              class="h-4 w-4 animate-spin"
            />
            <FlaskConical
              v-else
              class="h-4 w-4"
            />
            {{ pendingMode === 'dry' ? t('admin.tasks.running') : t('admin.tasks.dryRun') }}
          </Button>
          <Button
            variant="destructive"
            :disabled="!dryRunPassed || runTask.isPending.value"
            :title="dryRunPassed ? undefined : t('admin.tasks.dryRunFirst')"
            @click="confirmOpen = true"
          >
            <Play class="h-4 w-4" />
            {{ t('admin.tasks.apply') }}
          </Button>
          <span
            v-if="!dryRunPassed"
            class="text-xs text-muted-foreground"
          >
            {{ t('admin.tasks.dryRunFirst') }}
          </span>
        </template>

        <Button
          v-else
          :disabled="runTask.isPending.value"
          @click="onRun"
        >
          <Loader2
            v-if="pendingMode"
            class="h-4 w-4 animate-spin"
          />
          <Play
            v-else
            class="h-4 w-4"
          />
          {{ pendingMode ? t('admin.tasks.running') : t('admin.tasks.run') }}
        </Button>
      </template>

      <Button
        as-child
        variant="ghost"
        size="sm"
        class="w-fit sm:ml-auto"
      >
        <RouterLink :to="{ name: 'admin-audit-log', query: { action: historyAction } }">
          <History class="h-4 w-4" />
          {{ t('admin.tasks.history') }}
        </RouterLink>
      </Button>
    </div>

    <div
      v-if="lastRun"
      class="flex flex-col gap-1.5 border-t pt-3"
    >
      <p class="flex flex-wrap items-baseline gap-x-2 text-sm font-medium">
        {{ resultTitle }}
        <span class="text-xs font-normal tabular-nums text-muted-foreground">
          {{ lastRun.at.toLocaleTimeString() }}
        </span>
      </p>
      <pre
        class="max-h-80 overflow-auto rounded-lg bg-muted p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap break-all"
      >{{ resultJson }}</pre>
    </div>

    <AdminActionDialog
      v-model:open="confirmOpen"
      :title="t('admin.tasks.applyConfirmTitle', { name: task.name })"
      :description="t('admin.tasks.applyConfirmDesc')"
      :confirm-label="t('admin.tasks.apply')"
      :pending="pendingMode === 'apply'"
      @confirm="onConfirmApply"
    />
  </section>
</template>
