'use client';

import { Bar, BarChart, XAxis, YAxis } from 'recharts';

import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart';

/**
 * AdminBarChart — a single-series vertical bar chart on the template's shadcn
 * `chart` (recharts). No axes; the bar labels sit under the chart and in the
 * tooltip. The colour is `currentColor`: set it with a text-* class on a
 * wrapper, like template-vue's `chart/BarChart.vue`.
 */
export function AdminBarChart({
  values,
  labels,
  name,
  height = 160,
}: {
  values: number[];
  labels?: string[];
  /** Series name in the tooltip. */
  name?: string;
  height?: number;
}) {
  if (values.length === 0) return null;

  const config = {
    value: { label: name, color: 'currentColor' },
  } satisfies ChartConfig;
  const data = values.map((value, i) => ({
    label: labels?.[i] ?? String(i + 1),
    value,
  }));

  return (
    <div className="w-full">
      <ChartContainer
        config={config}
        className="aspect-auto w-full"
        style={{ height }}
      >
        <BarChart data={data} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
          <XAxis dataKey="label" hide />
          <YAxis hide domain={[0, 'dataMax']} />
          <ChartTooltip
            cursor={false}
            content={<ChartTooltipContent hideIndicator />}
          />
          <Bar
            dataKey="value"
            fill="var(--color-value)"
            fillOpacity={0.8}
            radius={2}
            isAnimationActive={false}
          />
        </BarChart>
      </ChartContainer>
      {labels && labels.length > 0 && (
        <div className="text-muted-foreground mt-1 flex justify-between text-[10px]">
          {labels.map((label, i) => (
            <span key={i}>{label}</span>
          ))}
        </div>
      )}
    </div>
  );
}
