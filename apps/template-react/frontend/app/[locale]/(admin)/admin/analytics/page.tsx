'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { AdminStateBlock } from '@/components/admin/AdminStateBlock';
import { AdminBarChart } from '@/components/admin/chart/AdminBarChart';
import { AdminLineChart } from '@/components/admin/chart/AdminLineChart';
import { StatCard } from '@/components/admin/StatCard';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAuth } from '@/hooks';
import { useGetMrrAdminAnalyticsMrrGet } from '@/src/gen/hooks/useGetMrrAdminAnalyticsMrrGet';
import { useGetRevenueKpisAdminAnalyticsRevenueKpisGet } from '@/src/gen/hooks/useGetRevenueKpisAdminAnalyticsRevenueKpisGet';
import { useGetRevenueTimeseriesAdminAnalyticsRevenueTimeseriesGet } from '@/src/gen/hooks/useGetRevenueTimeseriesAdminAnalyticsRevenueTimeseriesGet';
import { useGetStatisticsOverviewAdminStatisticsOverviewGet } from '@/src/gen/hooks/useGetStatisticsOverviewAdminStatisticsOverviewGet';
import { useGetSubscriptionBreakdownAdminAnalyticsSubscriptionBreakdownGet } from '@/src/gen/hooks/useGetSubscriptionBreakdownAdminAnalyticsSubscriptionBreakdownGet';
import { useGetSubscriptionTrendAdminAnalyticsSubscriptionTrendGet } from '@/src/gen/hooks/useGetSubscriptionTrendAdminAnalyticsSubscriptionTrendGet';
import type { RevenueSeries } from '@/src/gen/models/RevenueSeries';

const HEAVY_STALE = 5 * 60 * 1000;
const REVENUE_DAYS = 90;

const seriesTotal = (points: { amount: number }[]) =>
  points.reduce((sum, p) => sum + p.amount, 0);

/** First + last label, to keep the axis readable. */
const edgeLabels = (labels: string[]): string[] => {
  const first = labels[0];
  const last = labels[labels.length - 1];
  return first !== undefined && last !== undefined ? [first, last] : [];
};

/**
 * Admin → Analytics — money and subscription analytics from the core
 * `/admin/analytics/*` endpoints: paying users, ARPPU, period-over-period
 * revenue, MRR, churn and the subscription trend. It reads the database's
 * payment and subscription state; product-usage analytics belong in your event
 * analytics tool.
 *
 * Two in-screen tabs: Revenue and Subscriptions. Money is shown per currency
 * and never summed; non-cash series (Telegram Stars, gifts) are shown apart
 * from cash. The headline revenue reuses the Overview endpoint. The heavy
 * queries (revenue timeseries, subscription trend) get a long staleTime, and
 * the backend caches them in Redis. Every query waits for the role check, so
 * non-admins never fire them. Charts use the template's shadcn `chart`.
 *
 * Port of template-vue's `AdminAnalytics.vue`.
 */
export default function AdminAnalyticsPage() {
  const t = useTranslations('admin');
  const { isAdminOrOwner } = useAuth();
  const enabled = isAdminOrOwner;

  // Revenue granularity toggle (day | week).
  const [granularity, setGranularity] = useState<'day' | 'week'>('day');

  // ── Overview (reused for headline cards) ────────────────────────────────
  const overview = useGetStatisticsOverviewAdminStatisticsOverviewGet({
    query: { enabled, staleTime: 60 * 1000 },
  });
  const overviewRevenueRows = Object.entries(
    overview.data?.revenue.alltime ?? {}
  );

  // ── Revenue timeseries ──────────────────────────────────────────────────
  const revenue = useGetRevenueTimeseriesAdminAnalyticsRevenueTimeseriesGet(
    { granularity, days: REVENUE_DAYS },
    { query: { enabled, staleTime: HEAVY_STALE } }
  );
  const series = revenue.data?.series ?? [];
  const cashSeries = series.filter((s) => s.is_cash);
  const nonCashSeries = series.filter((s) => !s.is_cash);
  const revenueBuckets = revenue.data?.buckets ?? [];

  // ── Revenue KPIs (paying users / ARPPU / avg payment + growth) ───────────
  const revenueKpis = useGetRevenueKpisAdminAnalyticsRevenueKpisGet({
    query: { enabled, staleTime: 60 * 1000 },
  });
  const kpiRows = revenueKpis.data?.kpis ?? [];
  const growthRows = revenueKpis.data?.growth ?? [];

  // ── Subscriptions ───────────────────────────────────────────────────────
  const subTrend = useGetSubscriptionTrendAdminAnalyticsSubscriptionTrendGet(
    { weeks: 12 },
    { query: { enabled, staleTime: HEAVY_STALE } }
  );
  const subBreakdown =
    useGetSubscriptionBreakdownAdminAnalyticsSubscriptionBreakdownGet({
      query: { enabled, staleTime: 60 * 1000 },
    });
  const mrr = useGetMrrAdminAnalyticsMrrGet({
    query: { enabled, staleTime: 60 * 1000 },
  });

  const trendPoints = subTrend.data?.points ?? [];
  const trendBuckets = trendPoints.map((p) => p.bucket);
  const statusRows = Object.entries(subBreakdown.data?.by_status ?? {});
  const churnRows = Object.entries(subBreakdown.data?.churn_by_reason ?? {});
  const mrrRows = mrr.data?.rows ?? [];
  const breakdown = subBreakdown.data;

  const empty = (
    <p className="text-muted-foreground text-sm">{t('state.empty')}</p>
  );

  const seriesCard = (s: RevenueSeries, colorClass: string) => (
    <Card key={`${s.currency}-${s.provider}`}>
      <CardContent className="p-4">
        <div className="mb-1 flex items-center justify-between">
          <span className="text-sm font-medium">{s.currency}</span>
          <span className="text-muted-foreground text-xs">{s.provider}</span>
        </div>
        <div className="text-2xl font-bold tracking-tight">
          {seriesTotal(s.points).toLocaleString()} {s.currency}
        </div>
        <div className={`mt-2 ${colorClass}`}>
          <AdminLineChart
            points={s.points.map((p) => p.amount)}
            name={s.currency}
            pointLabels={s.points.map((p) => p.bucket)}
            edgeLabels={edgeLabels(revenueBuckets)}
          />
        </div>
      </CardContent>
    </Card>
  );

  return (
    <Tabs defaultValue="revenue" className="flex flex-col gap-4">
      <TabsList className="w-full justify-start overflow-x-auto">
        <TabsTrigger value="revenue">{t('analytics.tabs.revenue')}</TabsTrigger>
        <TabsTrigger value="subscriptions">
          {t('analytics.tabs.subscriptions')}
        </TabsTrigger>
      </TabsList>

      {/* ════════════════ REVENUE ════════════════ */}
      <TabsContent value="revenue" className="flex flex-col gap-4">
        {/* Headline cash revenue (per-currency, reused from overview) */}
        <AdminStateBlock
          isLoading={overview.isLoading}
          error={overview.error}
          isEmpty={!overview.data}
          onRetry={() => void overview.refetch()}
        >
          {overviewRevenueRows.length > 0 ? (
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
              {overviewRevenueRows.map(([currency, amount]) => (
                <StatCard
                  key={currency}
                  label={t('analytics.revenue.alltime', { currency })}
                  value={amount}
                  format="currency"
                  currency={currency}
                />
              ))}
            </div>
          ) : (
            empty
          )}
        </AdminStateBlock>

        {/* Paying users / ARPPU / avg payment (per currency, cash only) */}
        <AdminStateBlock
          isLoading={revenueKpis.isLoading}
          error={revenueKpis.error}
          isEmpty={!revenueKpis.data}
          onRetry={() => void revenueKpis.refetch()}
        >
          {kpiRows.length > 0 ? (
            <section className="flex flex-col gap-3">
              <h3 className="text-muted-foreground text-sm font-medium">
                {t('analytics.revenue.kpisTitle')}
              </h3>
              {kpiRows.map((row) => (
                <div key={row.currency} className="flex flex-col gap-2">
                  <span className="text-muted-foreground text-xs font-medium">
                    {row.currency}
                  </span>
                  <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                    <StatCard
                      label={t('analytics.revenue.payingUsers')}
                      value={row.paying_users}
                    />
                    <StatCard
                      label={t('analytics.revenue.arppu', {
                        currency: row.currency,
                      })}
                      value={row.arppu ?? 0}
                      format="currency"
                      currency={row.currency}
                      caveat={
                        row.arppu == null
                          ? t('analytics.revenue.noPayingUsers')
                          : undefined
                      }
                    />
                    <StatCard
                      label={t('analytics.revenue.avgPayment', {
                        currency: row.currency,
                      })}
                      value={row.avg_payment ?? 0}
                      format="currency"
                      currency={row.currency}
                    />
                  </div>
                </div>
              ))}
            </section>
          ) : (
            empty
          )}
        </AdminStateBlock>

        {/* Period-over-period revenue (this vs last, per currency) */}
        <AdminStateBlock
          isLoading={revenueKpis.isLoading}
          error={revenueKpis.error}
          isEmpty={!growthRows.length}
          onRetry={() => void revenueKpis.refetch()}
        >
          <section className="flex flex-col gap-3">
            <h3 className="text-muted-foreground text-sm font-medium">
              {t('analytics.revenue.growthTitle')}
            </h3>
            {growthRows.map((row) => (
              <div key={row.currency} className="flex flex-col gap-2">
                <span className="text-muted-foreground text-xs font-medium">
                  {row.currency}
                </span>
                <div className="grid grid-cols-2 gap-3">
                  <StatCard
                    label={t('analytics.revenue.thisMonth')}
                    value={row.this_month}
                    format="currency"
                    currency={row.currency}
                    deltaPct={row.month_growth_pct ?? null}
                    caveat={
                      row.month_growth_pct == null
                        ? t('analytics.revenue.noPrior')
                        : undefined
                    }
                  />
                  <StatCard
                    label={t('analytics.revenue.thisWeek')}
                    value={row.this_week}
                    format="currency"
                    currency={row.currency}
                    deltaPct={row.week_growth_pct ?? null}
                    caveat={
                      row.week_growth_pct == null
                        ? t('analytics.revenue.noPrior')
                        : undefined
                    }
                  />
                </div>
              </div>
            ))}
          </section>
        </AdminStateBlock>

        {/* Granularity toggle */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-muted-foreground text-xs font-medium">
            {t('analytics.revenue.granularity')}
          </span>
          <Button
            size="sm"
            variant={granularity === 'day' ? 'default' : 'outline'}
            onClick={() => {
              setGranularity('day');
            }}
          >
            {t('analytics.revenue.day')}
          </Button>
          <Button
            size="sm"
            variant={granularity === 'week' ? 'default' : 'outline'}
            onClick={() => {
              setGranularity('week');
            }}
          >
            {t('analytics.revenue.week')}
          </Button>
        </div>

        {/* Per-currency revenue charts */}
        <AdminStateBlock
          isLoading={revenue.isLoading}
          error={revenue.error}
          isEmpty={!series.length}
          onRetry={() => void revenue.refetch()}
        >
          <div className="flex flex-col gap-4">
            <section>
              <h3 className="text-muted-foreground mb-2 text-sm font-medium">
                {t('analytics.revenue.cash')}
              </h3>
              {cashSeries.length > 0 ? (
                <div className="grid gap-4 md:grid-cols-2">
                  {cashSeries.map((s) => seriesCard(s, 'text-primary'))}
                </div>
              ) : (
                empty
              )}
            </section>

            {/* Non-cash (XTR / GIFT) — clearly separate, never folded into cash */}
            {nonCashSeries.length > 0 && (
              <section>
                <h3 className="text-muted-foreground mb-2 text-sm font-medium">
                  {t('analytics.revenue.nonCash')}
                </h3>
                <p className="text-muted-foreground mb-2 text-xs">
                  {t('analytics.revenue.nonCashCaveat')}
                </p>
                <div className="grid gap-4 md:grid-cols-2">
                  {nonCashSeries.map((s) =>
                    seriesCard(s, 'text-muted-foreground')
                  )}
                </div>
              </section>
            )}
          </div>
        </AdminStateBlock>
      </TabsContent>

      {/* ════════════════ SUBSCRIPTIONS ════════════════ */}
      <TabsContent value="subscriptions" className="flex flex-col gap-4">
        {/* MRR + MoM growth (per currency, from active paid subs' product pricing) */}
        <AdminStateBlock
          isLoading={mrr.isLoading}
          error={mrr.error}
          isEmpty={!mrr.data}
          onRetry={() => void mrr.refetch()}
        >
          <section className="flex flex-col gap-3">
            <div className="flex items-baseline justify-between">
              <h3 className="text-muted-foreground text-sm font-medium">
                {t('analytics.mrr.title')}
              </h3>
              {(mrr.data?.excluded ?? 0) > 0 && (
                <span className="text-muted-foreground text-xs">
                  {t('analytics.mrr.excluded', {
                    count: mrr.data?.excluded ?? 0,
                  })}
                </span>
              )}
            </div>
            {mrrRows.length > 0 ? (
              <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
                {mrrRows.map((row) => (
                  <StatCard
                    key={row.currency}
                    label={t('analytics.mrr.label', { currency: row.currency })}
                    value={row.mrr}
                    format="currency"
                    currency={row.currency}
                    deltaPct={row.growth_pct ?? null}
                    caveat={
                      row.growth_pct == null
                        ? t('analytics.revenue.noPrior')
                        : t('analytics.mrr.caveat', {
                            count: row.subscriptions,
                          })
                    }
                  />
                ))}
              </div>
            ) : (
              empty
            )}
          </section>
        </AdminStateBlock>

        {/* Churn rate + net-new + active gift/paid split */}
        <AdminStateBlock
          isLoading={subBreakdown.isLoading}
          error={subBreakdown.error}
          isEmpty={!breakdown}
          onRetry={() => void subBreakdown.refetch()}
        >
          {breakdown && (
            <section className="flex flex-col gap-3">
              <h3 className="text-muted-foreground text-sm font-medium">
                {t('analytics.subscriptions.healthTitle')}
              </h3>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
                <StatCard
                  label={t('analytics.subscriptions.activePaid')}
                  value={breakdown.active_paid}
                />
                <StatCard
                  label={t('analytics.subscriptions.activeGifted')}
                  value={breakdown.active_gifted}
                  caveat={t('analytics.subscriptions.giftedCaveat')}
                />
                <StatCard
                  label={t('analytics.subscriptions.churnRate')}
                  value={(breakdown.churn_rate ?? 0) / 100}
                  format="percent"
                  caveat={
                    breakdown.churn_rate == null
                      ? t('analytics.subscriptions.churnNoBase')
                      : t('analytics.subscriptions.churnCaveat', {
                          days: breakdown.churn_period_days,
                        })
                  }
                />
                <StatCard
                  label={t('analytics.subscriptions.netNew')}
                  value={breakdown.net_new}
                  caveat={t('analytics.subscriptions.netNewCaveat', {
                    days: breakdown.churn_period_days,
                  })}
                />
                <StatCard
                  label={t('analytics.subscriptions.gifted')}
                  value={breakdown.gifted}
                />
              </div>
            </section>
          )}
        </AdminStateBlock>

        <AdminStateBlock
          isLoading={subTrend.isLoading}
          error={subTrend.error}
          isEmpty={!trendPoints.length}
          onRetry={() => void subTrend.refetch()}
        >
          <Card>
            <CardContent className="p-4">
              <h3 className="text-muted-foreground mb-3 text-sm font-medium">
                {t('analytics.subscriptions.trend')}
              </h3>
              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <p className="text-muted-foreground mb-1 text-xs">
                    {t('analytics.subscriptions.new')}
                  </p>
                  <div className="text-green-600 dark:text-green-400">
                    <AdminLineChart
                      points={trendPoints.map((p) => p.new)}
                      name={t('analytics.subscriptions.new')}
                      pointLabels={trendBuckets}
                      edgeLabels={edgeLabels(trendBuckets)}
                    />
                  </div>
                </div>
                <div>
                  <p className="text-muted-foreground mb-1 text-xs">
                    {t('analytics.subscriptions.active')}
                  </p>
                  <div className="text-primary">
                    <AdminLineChart
                      points={trendPoints.map((p) => p.active)}
                      name={t('analytics.subscriptions.active')}
                      pointLabels={trendBuckets}
                      edgeLabels={edgeLabels(trendBuckets)}
                    />
                  </div>
                </div>
                <div>
                  <p className="text-muted-foreground mb-1 text-xs">
                    {t('analytics.subscriptions.ended')}
                  </p>
                  <div className="text-red-600 dark:text-red-400">
                    <AdminLineChart
                      points={trendPoints.map((p) => p.ended)}
                      name={t('analytics.subscriptions.ended')}
                      pointLabels={trendBuckets}
                      edgeLabels={edgeLabels(trendBuckets)}
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </AdminStateBlock>

        <AdminStateBlock
          isLoading={subBreakdown.isLoading}
          error={subBreakdown.error}
          isEmpty={!breakdown}
          onRetry={() => void subBreakdown.refetch()}
        >
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardContent className="p-4">
                <h3 className="text-muted-foreground mb-3 text-sm font-medium">
                  {t('analytics.subscriptions.byStatus')}
                </h3>
                <div className="text-primary">
                  <AdminBarChart
                    values={statusRows.map(([, count]) => count)}
                    labels={statusRows.map(([status]) => status)}
                    name={t('analytics.subscriptions.byStatus')}
                  />
                </div>
                <div className="text-muted-foreground mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs">
                  {statusRows.map(([status, count]) => (
                    <span key={status}>
                      {status}:{' '}
                      <strong className="text-foreground">{count}</strong>
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <h3 className="text-muted-foreground mb-3 text-sm font-medium">
                  {t('analytics.subscriptions.churn')}
                </h3>
                {churnRows.length > 0 ? (
                  <ul className="space-y-1 text-sm">
                    {churnRows.map(([reason, count]) => (
                      <li
                        key={reason}
                        className="flex items-center justify-between"
                      >
                        <span className="text-muted-foreground">{reason}</span>
                        <span className="font-medium">{count}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  empty
                )}
              </CardContent>
            </Card>
          </div>
        </AdminStateBlock>
      </TabsContent>
    </Tabs>
  );
}
