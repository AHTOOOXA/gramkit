<script setup lang="ts">
import { computed, ref } from 'vue';
import { ArrowDownRight, ArrowUpRight, Info } from '@lucide/vue';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import Sparkline from './chart/Sparkline.vue';

/**
 * StatCard — a single KPI tile: label, big value, optional delta chip vs the
 * prior window, and an optional sparkline. Used across Overview and Analytics.
 * Uses shadcn Card + semantic tokens only (no custom colour system).
 *
 * TODO: extract to core when a third Vue app needs this (each Vue app keeps
 * its own copy for now, built on its own `ui/*` kit).
 */
const props = withDefaults(
  defineProps<{
    label: string;
    /** `null` = undefined (e.g. no data in the window): rendered as an em dash, never a misleading 0. */
    value: number | null;
    /** % change vs prior window; renders a green/red chip. Omit to hide. */
    deltaPct?: number | null;
    /** Coarse trend points (window summaries, not a true daily series). */
    sparklinePoints?: number[];
    format?: 'number' | 'currency' | 'percent';
    /** Currency code when format === 'currency'. */
    currency?: string;
    /** Optional caveat: an info button (focusable, labelled) that reveals the text on tap/click. */
    caveat?: string;
  }>(),
  {
    format: 'number',
    deltaPct: null,
    sparklinePoints: undefined,
    currency: undefined,
    caveat: undefined,
  },
);

const formattedValue = computed(() => {
  const v = props.value;
  if (v === null) return '—';
  if (props.format === 'percent') {
    return `${(v * 100).toFixed(1)}%`;
  }
  if (props.format === 'currency') {
    try {
      return new Intl.NumberFormat(undefined, {
        style: 'currency',
        currency: props.currency || 'USD',
        maximumFractionDigits: 2,
      }).format(v);
    } catch {
      // Unknown/non-ISO currency code (e.g. XTR) — fall back to a plain number.
      return `${v.toLocaleString()} ${props.currency ?? ''}`.trim();
    }
  }
  return v.toLocaleString();
});

const hasDelta = computed(
  () => props.value !== null && props.deltaPct !== null && props.deltaPct !== undefined,
);
// A `title` tooltip never shows on touch (Telegram WebView): the caveat is a disclosure instead.
const caveatOpen = ref(false);
const isPositive = computed(() => (props.deltaPct ?? 0) >= 0);
const deltaLabel = computed(() => {
  const d = props.deltaPct ?? 0;
  return `${d >= 0 ? '+' : ''}${d.toFixed(1)}%`;
});
</script>

<template>
  <Card class="overflow-hidden">
    <CardContent class="p-4">
      <div class="flex items-center gap-1.5">
        <span class="text-xs font-medium text-muted-foreground">{{ label }}</span>
        <button
          v-if="caveat"
          type="button"
          class="-m-1 rounded p-1 text-muted-foreground/70 hover:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          :aria-label="caveat"
          :aria-expanded="caveatOpen"
          :title="caveat"
          @click="caveatOpen = !caveatOpen"
        >
          <Info
            class="h-3 w-3"
            aria-hidden="true"
          />
        </button>
      </div>
      <p
        v-if="caveat && caveatOpen"
        class="mt-1 text-[11px] leading-snug text-muted-foreground"
      >
        {{ caveat }}
      </p>

      <div class="mt-1 flex items-end justify-between gap-2">
        <span
          :key="formattedValue"
          class="text-2xl font-bold tracking-tight motion-preset-pop motion-duration-[0.2s]"
        >
          {{ formattedValue }}
        </span>
        <span
          v-if="sparklinePoints && sparklinePoints.length"
          class="text-primary"
        >
          <Sparkline :points="sparklinePoints" />
        </span>
      </div>

      <div
        v-if="hasDelta"
        :class="cn(
          'mt-2 inline-flex items-center gap-0.5 rounded-md px-1.5 py-0.5 text-xs font-medium',
          isPositive
            ? 'bg-green-500/10 text-green-600 dark:text-green-400'
            : 'bg-red-500/10 text-red-600 dark:text-red-400',
        )"
      >
        <ArrowUpRight
          v-if="isPositive"
          class="h-3 w-3"
        />
        <ArrowDownRight
          v-else
          class="h-3 w-3"
        />
        {{ deltaLabel }}
      </div>
    </CardContent>
  </Card>
</template>
