<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { adminSections, type AdminSection } from '@app/admin/sections';
import { cn } from '@/lib/utils';

/**
 * AdminTabs — the admin sub-navigation, built from the section registry
 * (`@app/admin/sections`): every section with a `labelKey` gets a tab, so a new
 * section never needs a template edit here. Active state is a prefix match on
 * the route path (Users stays lit on /admin/users/:id), or an exact match when
 * the section sets `exact`. Scrolls sideways when the tabs don't fit a phone.
 */
const route = useRoute();
const { t } = useI18n();

const tabs = computed(() =>
  adminSections
    .filter((s): s is AdminSection & { labelKey: string } => !!s.labelKey)
    .map((s) => ({ ...s, href: `/admin/${s.path}` })),
);

const isActive = (tab: { href: string; exact?: boolean }) =>
  tab.exact
    ? route.path === tab.href
    : route.path === tab.href || route.path.startsWith(`${tab.href}/`);
</script>

<template>
  <nav
    class="-mx-[var(--page-padding-x)] flex gap-1 overflow-x-auto border-b border-border px-[var(--page-padding-x)] [scrollbar-width:none] md:mx-0 md:px-0"
  >
    <RouterLink
      v-for="tab in tabs"
      :key="tab.name"
      :to="tab.href"
      :aria-current="isActive(tab) ? 'page' : undefined"
      :class="cn(
        '-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium transition-colors',
        isActive(tab)
          ? 'border-primary text-foreground'
          : 'border-transparent text-muted-foreground hover:text-foreground',
      )"
    >
      {{ t(tab.labelKey) }}
    </RouterLink>
  </nav>
</template>
