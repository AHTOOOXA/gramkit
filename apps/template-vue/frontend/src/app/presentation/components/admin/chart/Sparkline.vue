<script setup lang="ts">
import { computed } from 'vue';

/**
 * Sparkline — a tiny trend line. Pure inline SVG, zero dependency, SSG-safe
 * (no window access). Points are an array of raw numbers; we normalize them to
 * the viewBox internally. Themeable via the `currentColor` stroke, so callers
 * set colour with a Tailwind text-* class.
 *
 * TODO: extract to core when a third Vue app needs this (each Vue app keeps
 * its own copy for now, built on its own `ui/*` kit).
 */
const props = withDefaults(
  defineProps<{
    points: number[];
    width?: number;
    height?: number;
    strokeWidth?: number;
  }>(),
  { width: 80, height: 24, strokeWidth: 1.5 },
);

const path = computed(() => {
  const pts = props.points;
  if (!pts || pts.length === 0) return '';
  if (pts.length === 1) {
    const y = props.height / 2;
    return `M0,${y} L${props.width},${y}`;
  }
  const min = Math.min(...pts);
  const max = Math.max(...pts);
  const range = max - min || 1;
  const stepX = props.width / (pts.length - 1);
  const pad = props.strokeWidth; // keep the stroke inside the viewBox
  const usableH = props.height - pad * 2;

  return pts
    .map((value, i) => {
      const x = i * stepX;
      // Invert Y so larger values render higher.
      const y = pad + usableH - ((value - min) / range) * usableH;
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(' ');
});

const hasData = computed(() => props.points && props.points.length > 0);
</script>

<template>
  <svg
    v-if="hasData"
    :width="width"
    :height="height"
    :viewBox="`0 0 ${width} ${height}`"
    fill="none"
    preserveAspectRatio="none"
    class="overflow-visible"
    aria-hidden="true"
  >
    <path
      :d="path"
      stroke="currentColor"
      :stroke-width="strokeWidth"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
  </svg>
</template>
