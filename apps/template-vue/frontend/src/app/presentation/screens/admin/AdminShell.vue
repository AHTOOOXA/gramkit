<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { ShieldAlert } from '@lucide/vue';
import { useAdminGuard } from '@app/composables/useAdminGuard';
import { Skeleton } from '@/components/ui/skeleton';
import AdminTabs from '@app/presentation/components/admin/AdminTabs.vue';

/**
 * AdminShell — layout for every /admin/* route. The router nests the sections
 * from `@app/admin/sections` under `/admin` as children, so the shell renders
 * the title and tabs once and swaps the active section in its `<RouterView>`
 * (App.vue keys its transition by the parent route, so the shell stays mounted
 * across tab and detail navigation).
 *
 * The single client-side role guard (useAdminGuard) runs here for all sections;
 * the backend RBAC is the real authority.
 */
const { isAdminOrOwner, isLoading } = useAdminGuard();
const { t } = useI18n();
</script>

<template>
  <div class="flex flex-col gap-4 pt-4 pb-[calc(var(--bottom-nav-height)+1rem)] md:py-6">
    <!-- Bottom padding clears the fixed mobile bottom nav (AppShell only pads
         for it on `meta.layout: 'tabs'` routes); the var is 0 on desktop. -->
    <!-- While auth resolves we render a neutral skeleton; the guard redirects
         non-admins once it knows. -->
    <template v-if="isLoading">
      <Skeleton class="h-8 w-40" />
      <Skeleton class="h-9 w-full" />
      <Skeleton class="h-40 w-full" />
    </template>

    <template v-else-if="isAdminOrOwner">
      <header>
        <h1 class="text-2xl font-semibold">{{ t('admin.nav.title') }}</h1>
      </header>

      <AdminTabs />

      <section class="min-w-0">
        <RouterView />
      </section>
    </template>

    <!-- Resolved-and-not-admin: the guard is mid-redirect; show a brief notice
         instead of flashing section content. -->
    <div
      v-else
      class="flex flex-col items-center gap-2 py-16 text-center text-muted-foreground"
    >
      <ShieldAlert class="h-8 w-8" />
      <p>{{ t('admin.state.forbidden') }}</p>
    </div>
  </div>
</template>
