<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import Logo from '@app/presentation/components/shared/Logo.vue';
import { GITHUB_URL, REACT_DEMO_URL } from '@/config/constants';

/**
 * Footer for the marketing page: logo, copyright and the project links (repo,
 * changelog, license, the React demo). Pads for the fixed bottom nav on mobile.
 */
const { t } = useI18n();
const year = new Date().getFullYear();

const links = computed(() => [
  { href: GITHUB_URL, label: t('footer.github') },
  { href: `${GITHUB_URL}/blob/main/CHANGELOG.md`, label: t('footer.changelog') },
  { href: `${GITHUB_URL}/blob/main/LICENSE`, label: t('footer.license') },
  { href: REACT_DEMO_URL, label: t('footer.reactDemo') },
]);
</script>

<template>
  <footer class="border-t bg-muted/30 pb-[var(--bottom-nav-height)] md:pb-0">
    <div class="mx-auto max-w-[var(--page-max-width)] px-[var(--page-padding-x)] py-8">
      <div class="flex flex-col items-center justify-between gap-4 md:flex-row">
        <Logo size="sm" :show-text="true" />
        <nav class="flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-sm text-muted-foreground">
          <a
            v-for="link in links"
            :key="link.href"
            :href="link.href"
            target="_blank"
            rel="noopener noreferrer"
            class="transition-colors hover:text-foreground"
          >
            {{ link.label }}
          </a>
          <span>© {{ year }} Gramkit</span>
        </nav>
      </div>
    </div>
  </footer>
</template>
