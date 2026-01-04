<script setup lang="ts">
import { ref, computed } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { Menu, X, Lock } from 'lucide-vue-next';
import { cn } from '@/lib/utils';
import Logo from '@app/presentation/components/shared/Logo.vue';
import LanguageToggle from '@app/presentation/components/shared/LanguageToggle.vue';
import ThemeToggle from '@app/presentation/components/shared/ThemeToggle.vue';
import ProfileDropdown from '@app/presentation/components/shared/ProfileDropdown.vue';
import { Button } from '@/components/ui/button';
import { usePlatform } from '@core/platform';
import { useAuth } from '@app/composables';
import { getVisibleNavItems, authCtaItem } from '@/config/navigation';
import { layoutConfig } from '@/config/layout';

const route = useRoute();
const { t } = useI18n();
const menuOpen = ref(false);
const { isAuthenticated, isAdmin, isOwner } = useAuth();
const { isTelegram } = usePlatform();

const { mobileLayout } = layoutConfig;

// Extra bottom padding for Telegram Mini App on mobile device with bottom tabs
const useTelegramMobilePadding = computed(() => isTelegram && mobileLayout === 'bottom-tabs');

const { mainNav, mobileNav, showLoginCta } = getVisibleNavItems({
  isAuthenticated: isAuthenticated.value,
  isAdmin: isAdmin.value,
  isOwner: isOwner.value,
});

const isActive = (href: string) => {
  if (href === '/') return route.path === '/';
  return route.path.startsWith(href);
};
</script>

<template>
  <!-- Mobile: Bottom nav (only shown when mobileLayout='bottom-tabs') -->
  <nav
    v-if="mobileLayout === 'bottom-tabs'"
    :class="cn(
      'fixed bottom-0 left-0 right-0 z-50 bg-background border-t border-border md:hidden',
      useTelegramMobilePadding && 'pb-4'
    )"
  >
    <div
      class="grid gap-1 px-4"
      :style="{ gridTemplateColumns: `repeat(${mobileNav.length + (showLoginCta ? 1 : 0)}, 1fr)` }"
    >
      <RouterLink
        v-for="item in mobileNav"
        :key="item.id"
        :to="item.lockedForGuests && !isAuthenticated ? '/login' : item.href"
        :class="cn(
          'flex flex-col items-center justify-center gap-1 py-3 transition-colors',
          isActive(item.href) ? 'text-primary' : 'text-muted-foreground hover:text-foreground',
          item.lockedForGuests && !isAuthenticated && 'opacity-75'
        )"
      >
        <component :is="item.icon" class="w-[22px] h-[22px] shrink-0" />
        <span class="text-[11px] leading-4 font-medium flex items-center gap-0.5">
          {{ t(item.labelKey) }}
          <Lock v-if="item.lockedForGuests && !isAuthenticated" class="w-2 h-2" />
        </span>
      </RouterLink>
      <RouterLink
        v-if="showLoginCta"
        :to="authCtaItem.href"
        class="flex flex-col items-center justify-center gap-1 py-3 transition-colors text-primary hover:text-primary/80"
      >
        <component :is="authCtaItem.icon" class="w-[22px] h-[22px] shrink-0" />
        <span class="text-[11px] leading-4 font-medium">{{ t(authCtaItem.labelKey) }}</span>
      </RouterLink>
    </div>
  </nav>

  <!-- Mobile: Hamburger header (only shown when mobileLayout='hamburger') -->
  <header v-if="mobileLayout === 'hamburger'" class="fixed top-0 left-0 right-0 z-50 border-b bg-background md:hidden">
    <div class="w-full px-4 flex h-14 items-center justify-between">
      <Logo size="sm" :show-text="true" />
      <Button
        variant="ghost"
        size="sm"
        class="cursor-pointer"
        :aria-label="menuOpen ? t('nav.closeMenu') : t('nav.openMenu')"
        @click="menuOpen = !menuOpen"
      >
        <X v-if="menuOpen" class="w-6 h-6" />
        <Menu v-else class="w-6 h-6" />
      </Button>
    </div>

    <!-- Mobile Menu Content - dropdown below header -->
    <div v-if="menuOpen" class="border-t bg-background">
      <div class="p-2">
        <RouterLink
          v-for="item in mainNav"
          :key="item.id"
          :to="item.lockedForGuests && !isAuthenticated ? '/login' : item.href"
          :class="cn(
            'flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors',
            isActive(item.href)
              ? 'bg-accent text-accent-foreground'
              : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
            item.lockedForGuests && !isAuthenticated && 'opacity-75'
          )"
          @click="menuOpen = false"
        >
          <component :is="item.icon" class="w-4 h-4" />
          <span class="flex items-center gap-1">
            {{ t(item.labelKey) }}
            <Lock v-if="item.lockedForGuests && !isAuthenticated" class="w-2.5 h-2.5" />
          </span>
        </RouterLink>
        <template v-if="showLoginCta">
          <div class="my-2 h-px bg-border" />
          <RouterLink
            :to="authCtaItem.href"
            class="flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium text-primary hover:bg-accent"
            @click="menuOpen = false"
          >
            <component :is="authCtaItem.icon" class="w-4 h-4" />
            <span>{{ t(authCtaItem.labelKey) }}</span>
          </RouterLink>
        </template>
        <div class="my-2 h-px bg-border" />
        <div class="flex items-center gap-1 px-1">
          <LanguageToggle />
          <ThemeToggle />
          <div class="flex-1" />
          <ProfileDropdown v-if="isAuthenticated" />
        </div>
      </div>
    </div>
  </header>

  <!-- Desktop: Top header with nav (always shown on desktop) -->
  <header class="fixed top-0 left-0 right-0 z-50 border-b bg-background/95 backdrop-blur hidden md:block">
    <div class="max-w-[var(--page-max-width)] mx-auto px-[var(--page-padding-x)]">
      <div class="flex items-center justify-between h-14">
        <!-- Left: Logo + Nav tabs -->
        <div class="flex items-center gap-6">
          <Logo size="md" :show-text="true" />
          <nav class="flex items-center gap-1">
            <RouterLink
              v-for="item in mainNav"
              :key="item.id"
              :to="item.lockedForGuests && !isAuthenticated ? '/login' : item.href"
              :class="cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap',
                isActive(item.href)
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted',
                item.lockedForGuests && !isAuthenticated && 'opacity-75'
              )"
            >
              <component :is="item.icon" class="w-4 h-4" />
              <span class="flex items-center gap-1">
                {{ t(item.labelKey) }}
                <Lock v-if="item.lockedForGuests && !isAuthenticated" class="w-2.5 h-2.5" />
              </span>
            </RouterLink>
          </nav>
        </div>

        <!-- Right: Controls -->
        <div class="flex items-center gap-2">
          <LanguageToggle />
          <ThemeToggle />
          <Button v-if="showLoginCta" as-child>
            <RouterLink :to="authCtaItem.href">
              <component :is="authCtaItem.icon" class="w-4 h-4 mr-2" />
              {{ t(authCtaItem.labelKey) }}
            </RouterLink>
          </Button>
          <ProfileDropdown v-if="isAuthenticated" />
        </div>
      </div>
    </div>
  </header>

  <!-- Spacer to prevent content from being hidden under fixed header -->
  <div v-if="mobileLayout === 'hamburger'" class="h-14 md:hidden" />
  <div class="hidden md:block h-14" />
</template>

<style scoped>
/* No additional styles needed - using Tailwind utility classes */
</style>
