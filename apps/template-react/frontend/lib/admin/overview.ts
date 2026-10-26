/**
 * Helpers for the admin Overview screen (`GET /admin/statistics/overview`).
 * Pure functions: no React, no i18n — the screens translate.
 *
 * The backend returns the generic blocks (users, revenue, subscriptions) plus
 * `cards`: KPI tiles an app registers on the server
 * (`core.services.admin_metrics.register_overview_card`). Each card names its
 * `section`; the screen renders one group per section.
 *
 * Port of `adminOverview.ts` in core/frontend (the Vue package).
 * TODO: extract to core/frontend-react when a second React app needs this.
 */

/** The fields of an Overview card these helpers read (the generated `OverviewCard` fits). */
export interface OverviewCardLike {
  key: string;
  section: string;
}

/** Cards of one section, in the order the backend returned them. */
export interface OverviewCardGroup<T extends OverviewCardLike> {
  section: string;
  cards: T[];
}

/**
 * Groups Overview cards by `section`. Sections keep first-seen order, so the
 * app's registration order is the render order.
 */
export function groupOverviewCards<T extends OverviewCardLike>(
  cards: readonly T[] | null | undefined
): OverviewCardGroup<T>[] {
  const groups = new Map<string, T[]>();
  for (const card of cards ?? []) {
    const group = groups.get(card.section);
    if (group) group.push(card);
    else groups.set(card.section, [card]);
  }
  return [...groups].map(([section, items]) => ({ section, cards: items }));
}

/**
 * Percent change of `current` vs the previous window. `null` when it is
 * undefined: no previous value, or growth from zero (0 → 0 is 0%).
 */
export function deltaPct(
  current: number,
  previous: number | null | undefined
): number | null {
  if (previous === null || previous === undefined) return null;
  if (previous === 0) return current === 0 ? 0 : null;
  return ((current - previous) / previous) * 100;
}
