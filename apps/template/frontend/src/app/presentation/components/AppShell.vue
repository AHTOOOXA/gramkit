<script setup lang="ts">
import { computed } from 'vue';
import { usePlatform } from '@core/platform';
import AppNav from './AppNav.vue';
import { layoutConfig } from '@/config/layout';

const props = withDefaults(defineProps<{
  variant?: 'default' | 'wide' | 'narrow' | 'full';
}>(), {
  variant: 'default',
});

const variantClasses = {
  default: 'max-w-[var(--page-max-width)]',
  wide: 'max-w-[90rem]',
  narrow: 'max-w-[40rem]',
  full: 'w-full',
} as const;

const { isTelegramMobile } = usePlatform();
const { mobileLayout } = layoutConfig;

const useMobilePadding = computed(() =>
  isTelegramMobile && mobileLayout === 'bottom-tabs'
);

const containerClass = computed(() => variantClasses[props.variant]);
</script>

<template>
  <div class="min-h-screen bg-background flex flex-col">
    <AppNav />
    <main
:class="[
      'flex-1 w-full mx-auto px-[var(--page-padding-x)] py-[var(--page-padding-y)] pb-[var(--bottom-nav-height)] md:pb-[var(--page-padding-y)]',
      containerClass,
      useMobilePadding && 'pt-2'
    ]">
      <slot />
    </main>
    <slot name="footer" />
  </div>
</template>
