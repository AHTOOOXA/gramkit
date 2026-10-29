<script setup lang="ts">
import { BRAND_ICONS, type BrandIconName } from './brandIcons';

/** A brand logo (Simple Icons path) in the current text colour. Decorative: always aria-hidden. */
defineProps<{ name: BrandIconName }>();
</script>

<template>
  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false">
    <path :d="BRAND_ICONS[name]" />
  </svg>
</template>
