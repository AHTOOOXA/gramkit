<script setup lang="ts">
import { computed } from 'vue';

/**
 * BarChart — a responsive single-series vertical bar chart. Pure inline SVG,
 * zero dependency, SSG-safe. Bars use `currentColor`; set colour via a text-*
 * class on the wrapper. No axes/tooltips in v1 (chart decision).
 *
 * TODO: extract to core when a third Vue app needs this (each Vue app keeps
 * its own copy for now, built on its own `ui/*` kit).
 */
const props = withDefaults(
  defineProps<{
    values: number[];
    labels?: string[];
    height?: number;
  }>(),
  { labels: undefined, height: 160 },
);

const VW = 300;

const bars = computed(() => {
  const vals = props.values ?? [];
  const vh = props.height;
  if (vals.length === 0) return [];

  const max = Math.max(...vals, 0) || 1;
  const gap = 4;
  const slot = VW / vals.length;
  const barW = Math.max(1, slot - gap);

  return vals.map((value, i) => {
    const h = (Math.max(0, value) / max) * vh;
    return {
      x: i * slot + gap / 2,
      y: vh - h,
      width: barW,
      height: h,
    };
  });
});

const hasData = computed(() => (props.values?.length ?? 0) > 0);
</script>

<template>
  <div class="w-full">
    <svg
      v-if="hasData"
      :viewBox="`0 0 ${VW} ${height}`"
      :height="height"
      width="100%"
      preserveAspectRatio="none"
      class="block w-full"
      role="img"
    >
      <rect
        v-for="(bar, i) in bars"
        :key="i"
        :x="bar.x"
        :y="bar.y"
        :width="bar.width"
        :height="bar.height"
        rx="2"
        fill="currentColor"
        class="opacity-80"
      />
    </svg>
    <div
      v-if="hasData && labels?.length"
      class="mt-1 flex justify-between text-[10px] text-muted-foreground"
    >
      <span
        v-for="(label, i) in labels"
        :key="i"
      >{{ label }}</span>
    </div>
  </div>
</template>
