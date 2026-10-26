'use client';

import { useState } from 'react';
import { ArrowDownRight, ArrowUpRight, Info } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Card, CardContent } from '@/components/ui/card';

import { Sparkline } from './chart/Sparkline';

export interface StatCardProps {
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
}

const formatValue = (
  value: number | null,
  format: StatCardProps['format'],
  currency?: string
): string => {
  if (value === null) return '—';
  if (format === 'percent') return `${(value * 100).toFixed(1)}%`;
  if (format === 'currency') {
    try {
      return new Intl.NumberFormat(undefined, {
        style: 'currency',
        currency: currency === undefined || currency === '' ? 'USD' : currency,
        maximumFractionDigits: 2,
      }).format(value);
    } catch {
      // Unknown/non-ISO currency code (e.g. XTR) — fall back to a plain number.
      return `${value.toLocaleString()} ${currency ?? ''}`.trim();
    }
  }
  return value.toLocaleString();
};

/**
 * StatCard — a single KPI tile: label, big value, optional delta chip vs the
 * prior window, and an optional sparkline. Used across Overview and Analytics.
 * Uses shadcn Card + semantic tokens only (no custom colour system).
 *
 * Port of template-vue's `StatCard.vue`.
 * TODO: extract to core/frontend-react when a second React app needs this.
 */
export function StatCard({
  label,
  value,
  deltaPct = null,
  sparklinePoints,
  format = 'number',
  currency,
  caveat,
}: StatCardProps) {
  // A `title` tooltip never shows on touch (Telegram WebView): the caveat is a disclosure instead.
  const [caveatOpen, setCaveatOpen] = useState(false);

  const formattedValue = formatValue(value, format, currency);
  const hasDelta = value !== null && deltaPct !== null;
  const delta = deltaPct ?? 0;
  const isPositive = delta >= 0;
  const deltaLabel = `${delta >= 0 ? '+' : ''}${delta.toFixed(1)}%`;

  return (
    <Card className="overflow-hidden">
      <CardContent className="p-4">
        <div className="flex items-center gap-1.5">
          <span className="text-muted-foreground text-xs font-medium">
            {label}
          </span>
          {caveat && (
            <button
              type="button"
              className="text-muted-foreground/70 hover:text-muted-foreground focus-visible:ring-ring -m-1 rounded p-1 focus-visible:ring-2 focus-visible:outline-none"
              aria-label={caveat}
              aria-expanded={caveatOpen}
              title={caveat}
              onClick={() => {
                setCaveatOpen((open) => !open);
              }}
            >
              <Info className="h-3 w-3" aria-hidden="true" />
            </button>
          )}
        </div>
        {caveat && caveatOpen && (
          <p className="text-muted-foreground mt-1 text-[11px] leading-snug">
            {caveat}
          </p>
        )}

        <div className="mt-1 flex items-end justify-between gap-2">
          <span
            key={formattedValue}
            className="motion-preset-pop motion-duration-[0.2s] text-2xl font-bold tracking-tight"
          >
            {formattedValue}
          </span>
          {sparklinePoints && sparklinePoints.length > 0 && (
            <span className="text-primary">
              <Sparkline points={sparklinePoints} />
            </span>
          )}
        </div>

        {hasDelta && (
          <div
            className={cn(
              'mt-2 inline-flex items-center gap-0.5 rounded-md px-1.5 py-0.5 text-xs font-medium',
              isPositive
                ? 'bg-green-500/10 text-green-600 dark:text-green-400'
                : 'bg-red-500/10 text-red-600 dark:text-red-400'
            )}
          >
            {isPositive ? (
              <ArrowUpRight className="h-3 w-3" />
            ) : (
              <ArrowDownRight className="h-3 w-3" />
            )}
            {deltaLabel}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
