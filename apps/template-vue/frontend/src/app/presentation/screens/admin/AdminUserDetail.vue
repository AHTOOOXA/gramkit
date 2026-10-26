<script setup lang="ts">
import { computed, defineAsyncComponent, markRaw } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useQueryClient } from '@tanstack/vue-query';
import { ArrowLeft } from '@lucide/vue';
import { useAuth } from '@app/composables/useAuth';
import { adminUserPanels } from '@app/admin/userPanels';
import { formatDate, roleVariant, userLabel } from '@app/admin/format';
import { useAdminLabels } from '@app/admin/useAdminLabels';
import { useGetUserDetailAdminUsersUserIdGet } from '@gen/hooks/useGetUserDetailAdminUsersUserIdGet';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import AdminStateBlock from '@app/presentation/components/admin/AdminStateBlock.vue';
import AdminUserActions from '@app/presentation/components/admin/users/AdminUserActions.vue';

/**
 * AdminUserDetail — one user: profile card, the actions panel, and a tab per
 * entry in `adminUserPanels` (payments and subscriptions from core, plus any
 * the app registers in `@app/admin/app-userPanels.ts`). Each panel gets
 * `:user-id` and owns its own query.
 *
 * After any mutation (an action here, or a panel's `mutated`) it refetches the
 * profile and invalidates every `/admin/users/:user_id/...` query, which covers
 * the core panels and app panels alike.
 */
const { t } = useI18n();
const { isAdminOrOwner } = useAuth();
const { roleLabel, userTypeLabel } = useAdminLabels();
const route = useRoute();
const router = useRouter();
const queryClient = useQueryClient();

const userId = computed(() => String(route.params.id ?? ''));

const { data: user, isLoading, error, refetch } = useGetUserDetailAdminUsersUserIdGet(userId, {
  query: { enabled: () => isAdminOrOwner.value && !!userId.value, staleTime: 15 * 1000 },
});

// Built once per mount; markRaw keeps Vue from making the components reactive.
const panels = adminUserPanels.map((panel) => ({
  key: panel.key,
  labelKey: panel.labelKey,
  component: markRaw(defineAsyncComponent(panel.loader)),
}));

const initials = computed(() => (user.value ? userLabel(user.value).charAt(0).toUpperCase() : '?'));

const onMutated = () => {
  void refetch();
  // Kubb query keys look like [{ url: '/admin/users/:user_id/payments', params }, query].
  void queryClient.invalidateQueries({
    predicate: (q) =>
      String((q.queryKey[0] as { url?: string } | undefined)?.url ?? '').startsWith('/admin/users/:user_id/'),
  });
};

const onReset = () => {
  // The user no longer exists; drop cached lists and go back to them.
  void queryClient.invalidateQueries({
    predicate: (q) =>
      String((q.queryKey[0] as { url?: string } | undefined)?.url ?? '').startsWith('/admin/users'),
  });
  void router.push({ name: 'admin-users' });
};
</script>

<template>
  <div class="flex flex-col gap-4">
    <Button
      variant="ghost"
      size="sm"
      class="-ml-2 w-fit"
      @click="router.push({ name: 'admin-users' })"
    >
      <ArrowLeft class="h-4 w-4" />
      {{ t('admin.users.backToList') }}
    </Button>

    <AdminStateBlock
      :is-loading="isLoading"
      :error="error"
      @retry="refetch()"
    >
      <template #loading>
        <div class="flex flex-col gap-4">
          <Skeleton class="h-32 w-full rounded-xl" />
          <Skeleton class="h-28 w-full rounded-xl" />
          <Skeleton class="h-48 w-full rounded-xl" />
        </div>
      </template>

      <div
        v-if="user"
        class="flex flex-col gap-4"
      >
        <!-- Profile -->
        <section class="flex flex-col gap-4 rounded-xl border bg-card p-4">
          <div class="flex items-start gap-3">
            <Avatar class="size-12 shrink-0">
              <AvatarImage
                v-if="user.avatar_url"
                :src="user.avatar_url"
                :alt="userLabel(user)"
              />
              <AvatarFallback>{{ initials }}</AvatarFallback>
            </Avatar>
            <div class="flex min-w-0 flex-col gap-1.5">
              <h2 class="break-words text-lg font-semibold leading-tight">
                {{ userLabel(user) }}
              </h2>
              <div class="flex flex-wrap items-center gap-1.5">
                <Badge :variant="roleVariant(user.role)">{{ roleLabel(user.role) }}</Badge>
                <Badge variant="outline">{{ userTypeLabel(user.user_type) }}</Badge>
                <Badge
                  v-if="user.has_active_subscription"
                  variant="default"
                >
                  {{ t('admin.users.profile.subActive') }}
                </Badge>
              </div>
            </div>
          </div>

          <dl class="grid grid-cols-1 gap-x-6 gap-y-3 text-sm sm:grid-cols-3">
            <div class="flex min-w-0 flex-col gap-0.5">
              <dt class="text-xs text-muted-foreground">{{ t('admin.users.profile.telegram') }}</dt>
              <dd class="break-words">
                <span class="tabular-nums">{{ user.telegram_id ?? '—' }}</span>
                <span
                  v-if="user.tg_username"
                  class="text-muted-foreground"
                > · @{{ user.tg_username }}</span>
              </dd>
            </div>
            <div class="flex min-w-0 flex-col gap-0.5">
              <dt class="text-xs text-muted-foreground">{{ t('admin.users.profile.email') }}</dt>
              <dd class="break-all">{{ user.email ?? '—' }}</dd>
            </div>
            <div class="flex min-w-0 flex-col gap-0.5">
              <dt class="text-xs text-muted-foreground">{{ t('admin.users.profile.joined') }}</dt>
              <dd>{{ formatDate(user.created_at, true) }}</dd>
            </div>
          </dl>
        </section>

        <!-- Actions -->
        <AdminUserActions
          :user="user"
          @mutated="onMutated"
          @reset="onReset"
        />

        <!-- Panels -->
        <Tabs
          v-if="panels.length"
          :default-value="panels[0].key"
          class="w-full gap-3"
        >
          <TabsList class="max-w-full justify-start overflow-x-auto">
            <TabsTrigger
              v-for="panel in panels"
              :key="panel.key"
              :value="panel.key"
              class="flex-none"
            >
              {{ t(panel.labelKey) }}
            </TabsTrigger>
          </TabsList>

          <TabsContent
            v-for="panel in panels"
            :key="panel.key"
            :value="panel.key"
          >
            <component
              :is="panel.component"
              :user-id="userId"
              @mutated="onMutated"
            />
          </TabsContent>
        </Tabs>
      </div>
    </AdminStateBlock>
  </div>
</template>
