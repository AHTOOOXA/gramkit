<script setup lang="ts">
import { computed } from 'vue';

/**
 * LineChart — a responsive single-series line chart. Pure inline SVG, zero
 * dependency, SSG-safe. No axes/tooltips (v1 scope per the chart decision);
 * escalate to Unovis only when a panel genuinely needs them. Themeable via
 * `currentColor` — set colour with a text-* class on the wrapper.
 *
 * TODO: extract to core when a third Vue app needs this (each Vue app keeps
 * its own copy for now, built on its own `ui/*` kit).
 */
const props = withDefaults(
  defineProps<{
    points: number[];
    /** Optional x-axis labels, rendered evenly under the line. */
    labels?: string[];
    height?: number;
    /** Fill the area under the line with a faint tint. */
    area?: boolean;
  }>(),
  { labels: undefined, height: 160, area: true },
);

// Fixed viewBox; the SVG scales to its container width via preserveAspectRatio.
const VW = 300;

const geometry = computed(() => {
  const pts = props.points ?? [];
  const vh = props.height;
  if (pts.length === 0) return { line: '', area: '' };

  const min = Math.min(...pts, 0);
  const max = Math.max(...pts);
  const range = max - min || 1;
  const pad = 4;
  const usableH = vh - pad * 2;
  const stepX = pts.length > 1 ? VW / (pts.length - 1) : 0;

  const coords = pts.map((value, i) => {
    const x = pts.length > 1 ? i * stepX : VW / 2;
    const y = pad + usableH - ((value - min) / range) * usableH;
    return [x, y] as const;
  });

  const line = coords
    .map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`)
    .join(' ');

  const first = coords[0];
  const last = coords[coords.length - 1];
  const area = `${line} L${last[0].toFixed(2)},${vh} L${first[0].toFixed(2)},${vh} Z`;

  return { line, area };
});

const hasData = computed(() => (props.points?.length ?? 0) > 0);
</script>

<template>
  <div class="w-full">
    <svg
      v-if="hasData"
      :viewBox="`0 0 ${VW} ${height}`"
      :height="height"
      width="100%"
      fill="none"
      preserveAspectRatio="none"
      class="block w-full"
      role="img"
    >
      <path
        v-if="area"
        :d="geometry.area"
        fill="currentColor"
        class="opacity-10"
      />
      <path
        :d="geometry.line"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        vector-effect="non-scaling-stroke"
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
