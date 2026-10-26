'use client';

import { Area, AreaChart, XAxis, YAxis } from 'recharts';

import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart';

/**
 * AdminLineChart — a single-series line (with a faint area) on the template's
 * shadcn `chart` (recharts). No axes; a tooltip shows the point. The colour is
 * `currentColor`: set it with a text-* class on a wrapper, like template-vue's
 * `chart/LineChart.vue`. `edgeLabels` render under the chart (first / last
 * bucket); `pointLabels` name each point in the tooltip.
 */
export function AdminLineChart({
  points,
  name,
  pointLabels,
  edgeLabels,
  height = 160,
  area = true,
}: {
  points: number[];
  /** Series name in the tooltip. */
  name?: string;
  pointLabels?: string[];
  edgeLabels?: string[];
  height?: number;
  area?: boolean;
}) {
  if (points.length === 0) return null;

  const config = {
    value: { label: name, color: 'currentColor' },
  } satisfies ChartConfig;
  const data = points.map((value, i) => ({
    label: pointLabels?.[i] ?? String(i + 1),
    value,
  }));

  return (
    <div className="w-full">
      <ChartContainer
        config={config}
        className="aspect-auto w-full"
        style={{ height }}
      >
        <AreaChart
          data={data}
          margin={{ top: 4, right: 0, bottom: 4, left: 0 }}
        >
          <XAxis dataKey="label" hide />
          <YAxis hide domain={[(min: number) => Math.min(min, 0), 'dataMax']} />
          <ChartTooltip
            cursor={false}
            content={<ChartTooltipContent indicator="line" />}
          />
          <Area
            dataKey="value"
            type="linear"
            stroke="var(--color-value)"
            strokeWidth={2}
            fill="var(--color-value)"
            fillOpacity={area ? 0.1 : 0}
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ChartContainer>
      {edgeLabels && edgeLabels.length > 0 && (
        <div className="text-muted-foreground mt-1 flex justify-between text-[10px]">
          {edgeLabels.map((label, i) => (
            <span key={i}>{label}</span>
          ))}
        </div>
      )}
    </div>
  );
}
