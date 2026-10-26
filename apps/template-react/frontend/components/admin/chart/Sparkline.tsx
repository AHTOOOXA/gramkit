/**
 * Sparkline — a tiny trend line inside a KPI tile (`StatCard`). Inline SVG on
 * purpose: an 80×24 decoration doesn't need recharts' measuring container.
 * Points are raw numbers, normalized to the viewBox; the stroke is
 * `currentColor`, so callers colour it with a text-* class.
 *
 * Port of template-vue's `chart/Sparkline.vue`.
 */
export function Sparkline({
  points,
  width = 80,
  height = 24,
  strokeWidth = 1.5,
}: {
  points: number[];
  width?: number;
  height?: number;
  strokeWidth?: number;
}) {
  if (points.length === 0) return null;

  let path: string;
  if (points.length === 1) {
    const y = height / 2;
    path = `M0,${String(y)} L${String(width)},${String(y)}`;
  } else {
    const min = Math.min(...points);
    const max = Math.max(...points);
    const range = max - min || 1;
    const stepX = width / (points.length - 1);
    const pad = strokeWidth; // keep the stroke inside the viewBox
    const usableH = height - pad * 2;
    path = points
      .map((value, i) => {
        const x = i * stepX;
        // Invert Y so larger values render higher.
        const y = pad + usableH - ((value - min) / range) * usableH;
        return `${i === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`;
      })
      .join(' ');
  }

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${String(width)} ${String(height)}`}
      fill="none"
      preserveAspectRatio="none"
      className="overflow-visible"
      aria-hidden="true"
    >
      <path
        d={path}
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
