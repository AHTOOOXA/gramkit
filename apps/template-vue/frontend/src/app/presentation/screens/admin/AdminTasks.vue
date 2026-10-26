<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { Info } from '@lucide/vue';
import { useAuth } from '@app/composables/useAuth';
import { useListTasksAdminTasksGet } from '@gen/hooks/useListTasksAdminTasksGet';
import type { AdminTaskInfo } from '@gen/models/AdminTaskInfo';
import { Skeleton } from '@/components/ui/skeleton';
import AdminStateBlock from '@app/presentation/components/admin/AdminStateBlock.vue';
import AdminTaskCard from '@app/presentation/components/admin/tasks/AdminTaskCard.vue';

/**
 * AdminTasks — the maintenance tasks registered with `@admin_task` on the
 * backend (`app/services/admin_tasks.py`, framework in core), one
 * AdminTaskCard each. Tasks run inside the live server, in the request's
 * transaction, and every run is audit-logged as `admin_task:<name>`.
 *
 * Any admin sees the list; only the owner gets the run controls (the backend
 * answers 403 to anyone else either way).
 */
const { t } = useI18n();
const { isAdminOrOwner, isOwner } = useAuth();

const { data, isLoading, error, refetch } = useListTasksAdminTasksGet({
  query: {
    enabled: () => isAdminOrOwner.value,
    staleTime: 5 * 60 * 1000,
  },
});

const tasks = computed<AdminTaskInfo[]>(() => data.value ?? []);
</script>

<template>
  <div class="flex flex-col gap-4">
    <p class="text-sm text-muted-foreground">{{ t('admin.tasks.description') }}</p>

    <p
      v-if="!isOwner"
      class="flex items-start gap-1.5 text-xs text-muted-foreground"
    >
      <Info class="mt-0.5 h-3.5 w-3.5 shrink-0" />
      {{ t('admin.tasks.ownerOnly') }}
    </p>

    <AdminStateBlock
      :is-loading="isLoading"
      :error="error"
      :is-empty="!tasks.length"
      @retry="refetch()"
    >
      <template #loading>
        <div class="flex flex-col gap-3">
          <Skeleton
            v-for="i in 2"
            :key="i"
            class="h-32 w-full rounded-xl"
          />
        </div>
      </template>

      <template #empty>
        <div
          class="flex flex-col items-center justify-center rounded-xl border border-dashed border-border py-12 text-center text-sm text-muted-foreground"
        >
          {{ t('admin.tasks.empty') }}
        </div>
      </template>

      <div class="flex flex-col gap-3">
        <AdminTaskCard
          v-for="task in tasks"
          :key="task.name"
          :task="task"
          :can-run="isOwner"
        />
      </div>
    </AdminStateBlock>
  </div>
</template>
