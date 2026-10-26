<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAuth } from '@app/composables/useAuth';
import { useGetStatisticsOverviewAdminStatisticsOverviewGet } from '@gen/hooks/useGetStatisticsOverviewAdminStatisticsOverviewGet';
import { useGetRevenueTimeseriesAdminAnalyticsRevenueTimeseriesGet } from '@gen/hooks/useGetRevenueTimeseriesAdminAnalyticsRevenueTimeseriesGet';
import { useGetRevenueKpisAdminAnalyticsRevenueKpisGet } from '@gen/hooks/useGetRevenueKpisAdminAnalyticsRevenueKpisGet';
import { useGetSubscriptionTrendAdminAnalyticsSubscriptionTrendGet } from '@gen/hooks/useGetSubscriptionTrendAdminAnalyticsSubscriptionTrendGet';
import { useGetSubscriptionBreakdownAdminAnalyticsSubscriptionBreakdownGet } from '@gen/hooks/useGetSubscriptionBreakdownAdminAnalyticsSubscriptionBreakdownGet';
import { useGetMrrAdminAnalyticsMrrGet } from '@gen/hooks/useGetMrrAdminAnalyticsMrrGet';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import StatCard from '@app/presentation/components/admin/StatCard.vue';
import AdminStateBlock from '@app/presentation/components/admin/AdminStateBlock.vue';
import LineChart from '@app/presentation/components/admin/chart/LineChart.vue';
import BarChart from '@app/presentation/components/admin/chart/BarChart.vue';

/**
 * AdminAnalytics — money and subscription analytics from the core
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
 * non-admins never fire them.
 */
const { t } = useI18n();
const { isAdminOrOwner } = useAuth();

const HEAVY_STALE = 5 * 60 * 1000;
const enabled = () => isAdminOrOwner.value;

// Revenue granularity toggle (day | week).
const granularity = ref<'day' | 'week'>('day');
const revenueDays = ref(90);

// ── Overview (reused for headline cards) ──────────────────────────────────
const overview = useGetStatisticsOverviewAdminStatisticsOverviewGet({
  query: { enabled, staleTime: 60 * 1000 },
});

// ── Revenue timeseries ────────────────────────────────────────────────────
const revenueParams = computed(() => ({
  granularity: granularity.value,
  days: revenueDays.value,
}));
const revenue = useGetRevenueTimeseriesAdminAnalyticsRevenueTimeseriesGet(revenueParams, {
  query: { enabled, staleTime: HEAVY_STALE },
});

const cashSeries = computed(() => (revenue.data.value?.series ?? []).filter((s) => s.is_cash));
const nonCashSeries = computed(() => (revenue.data.value?.series ?? []).filter((s) => !s.is_cash));
const revenueBuckets = computed(() => revenue.data.value?.buckets ?? []);
/** Short labels (first + last bucket) to keep the axis readable. */
const revenueLabels = computed(() => {
  const b = revenueBuckets.value;
  return b.length ? [b[0], b[b.length - 1]] : [];
});
const seriesTotal = (points: { amount: number }[]) =>
  points.reduce((sum, p) => sum + p.amount, 0);

// Headline cash revenue cards from the overview (per-currency, never summed).
const overviewRevenueRows = computed(() => {
  const alltime = overview.data.value?.revenue?.alltime ?? {};
  return Object.entries(alltime).map(([currency, amount]) => ({ currency, amount }));
});

// ── Revenue KPIs (paying users / ARPPU / avg payment + growth) ─────────────
const revenueKpis = useGetRevenueKpisAdminAnalyticsRevenueKpisGet({
  query: { enabled, staleTime: 60 * 1000 },
});
const kpiRows = computed(() => revenueKpis.data.value?.kpis ?? []);
const growthRows = computed(() => revenueKpis.data.value?.growth ?? []);

// ── Subscriptions ─────────────────────────────────────────────────────────
const subTrend = useGetSubscriptionTrendAdminAnalyticsSubscriptionTrendGet(
  { weeks: 12 },
  { query: { enabled, staleTime: HEAVY_STALE } },
);
const subBreakdown = useGetSubscriptionBreakdownAdminAnalyticsSubscriptionBreakdownGet({
  query: { enabled, staleTime: 60 * 1000 },
});
const mrr = useGetMrrAdminAnalyticsMrrGet({
  query: { enabled, staleTime: 60 * 1000 },
});

const subNewSeries = computed(() => (subTrend.data.value?.points ?? []).map((p) => p.new));
const subActiveSeries = computed(() => (subTrend.data.value?.points ?? []).map((p) => p.active));
const subEndedSeries = computed(() => (subTrend.data.value?.points ?? []).map((p) => p.ended));
const subTrendLabels = computed(() => {
  const pts = subTrend.data.value?.points ?? [];
  return pts.length ? [pts[0].bucket, pts[pts.length - 1].bucket] : [];
});
const statusRows = computed(() =>
  Object.entries(subBreakdown.data.value?.by_status ?? {}).map(([status, count]) => ({
    status,
    count,
  })),
);
const statusValues = computed(() => statusRows.value.map((r) => r.count));
const statusLabels = computed(() => statusRows.value.map((r) => r.status));
const churnRows = computed(() =>
  Object.entries(subBreakdown.data.value?.churn_by_reason ?? {}).map(([reason, count]) => ({
    reason,
    count,
  })),
);
const mrrRows = computed(() => mrr.data.value?.rows ?? []);

const isEmpty = (data: unknown) => data === undefined || data === null;
</script>

<template>
  <Tabs
    default-value="revenue"
    class="flex flex-col gap-4"
  >
    <TabsList class="w-full justify-start overflow-x-auto">
      <TabsTrigger value="revenue">{{ t('admin.analytics.tabs.revenue') }}</TabsTrigger>
      <TabsTrigger value="subscriptions">{{ t('admin.analytics.tabs.subscriptions') }}</TabsTrigger>
    </TabsList>

    <!-- ════════════════ REVENUE ════════════════ -->
    <TabsContent
      value="revenue"
      class="flex flex-col gap-4"
    >
      <!-- Headline cash revenue (per-currency, reused from overview) -->
      <AdminStateBlock
        :is-loading="overview.isLoading.value"
        :error="overview.error.value"
        :is-empty="isEmpty(overview.data.value)"
        @retry="overview.refetch()"
      >
        <div
          v-if="overviewRevenueRows.length"
          class="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4"
        >
          <StatCard
            v-for="row in overviewRevenueRows"
            :key="row.currency"
            :label="t('admin.analytics.revenue.alltime', { currency: row.currency })"
            :value="row.amount"
            format="currency"
            :currency="row.currency"
          />
        </div>
        <p
          v-else
          class="text-sm text-muted-foreground"
        >
          {{ t('admin.state.empty') }}
        </p>
      </AdminStateBlock>

      <!-- Paying users / ARPPU / avg payment (per currency, cash only) -->
      <AdminStateBlock
        :is-loading="revenueKpis.isLoading.value"
        :error="revenueKpis.error.value"
        :is-empty="isEmpty(revenueKpis.data.value)"
        @retry="revenueKpis.refetch()"
      >
        <section
          v-if="kpiRows.length"
          class="flex flex-col gap-3"
        >
          <h3 class="text-sm font-medium text-muted-foreground">
            {{ t('admin.analytics.revenue.kpisTitle') }}
          </h3>
          <div
            v-for="row in kpiRows"
            :key="row.currency"
            class="flex flex-col gap-2"
          >
            <span class="text-xs font-medium text-muted-foreground">{{ row.currency }}</span>
            <div class="grid grid-cols-2 gap-3 md:grid-cols-3">
              <StatCard
                :label="t('admin.analytics.revenue.payingUsers')"
                :value="row.paying_users"
              />
              <StatCard
                :label="t('admin.analytics.revenue.arppu', { currency: row.currency })"
                :value="row.arppu ?? 0"
                format="currency"
                :currency="row.currency"
                :caveat="row.arppu === null ? t('admin.analytics.revenue.noPayingUsers') : undefined"
              />
              <StatCard
                :label="t('admin.analytics.revenue.avgPayment', { currency: row.currency })"
                :value="row.avg_payment ?? 0"
                format="currency"
                :currency="row.currency"
              />
            </div>
          </div>
        </section>
        <p
          v-else
          class="text-sm text-muted-foreground"
        >
          {{ t('admin.state.empty') }}
        </p>
      </AdminStateBlock>

      <!-- Period-over-period revenue (this vs last, per currency) -->
      <AdminStateBlock
        :is-loading="revenueKpis.isLoading.value"
        :error="revenueKpis.error.value"
        :is-empty="!growthRows.length"
        @retry="revenueKpis.refetch()"
      >
        <section class="flex flex-col gap-3">
          <h3 class="text-sm font-medium text-muted-foreground">
            {{ t('admin.analytics.revenue.growthTitle') }}
          </h3>
          <div
            v-for="row in growthRows"
            :key="row.currency"
            class="flex flex-col gap-2"
          >
            <span class="text-xs font-medium text-muted-foreground">{{ row.currency }}</span>
            <div class="grid grid-cols-2 gap-3">
              <StatCard
                :label="t('admin.analytics.revenue.thisMonth')"
                :value="row.this_month"
                format="currency"
                :currency="row.currency"
                :delta-pct="row.month_growth_pct"
                :caveat="row.month_growth_pct === null ? t('admin.analytics.revenue.noPrior') : undefined"
              />
              <StatCard
                :label="t('admin.analytics.revenue.thisWeek')"
                :value="row.this_week"
                format="currency"
                :currency="row.currency"
                :delta-pct="row.week_growth_pct"
                :caveat="row.week_growth_pct === null ? t('admin.analytics.revenue.noPrior') : undefined"
              />
            </div>
          </div>
        </section>
      </AdminStateBlock>

      <!-- Granularity toggle + window -->
      <div class="flex flex-wrap items-center gap-2">
        <span class="text-xs font-medium text-muted-foreground">
          {{ t('admin.analytics.revenue.granularity') }}
        </span>
        <Button
          size="sm"
          :variant="granularity === 'day' ? 'default' : 'outline'"
          @click="granularity = 'day'"
        >
          {{ t('admin.analytics.revenue.day') }}
        </Button>
        <Button
          size="sm"
          :variant="granularity === 'week' ? 'default' : 'outline'"
          @click="granularity = 'week'"
        >
          {{ t('admin.analytics.revenue.week') }}
        </Button>
      </div>

      <!-- Per-currency revenue charts -->
      <AdminStateBlock
        :is-loading="revenue.isLoading.value"
        :error="revenue.error.value"
        :is-empty="!revenue.data.value?.series?.length"
        @retry="revenue.refetch()"
      >
        <div class="flex flex-col gap-4">
          <section>
            <h3 class="mb-2 text-sm font-medium text-muted-foreground">
              {{ t('admin.analytics.revenue.cash') }}
            </h3>
            <div
              v-if="cashSeries.length"
              class="grid gap-4 md:grid-cols-2"
            >
              <Card
                v-for="s in cashSeries"
                :key="`${s.currency}-${s.provider}`"
              >
                <CardContent class="p-4">
                  <div class="mb-1 flex items-center justify-between">
                    <span class="text-sm font-medium">{{ s.currency }}</span>
                    <span class="text-xs text-muted-foreground">{{ s.provider }}</span>
                  </div>
                  <div class="text-2xl font-bold tracking-tight">
                    {{ seriesTotal(s.points).toLocaleString() }} {{ s.currency }}
                  </div>
                  <div class="mt-2 text-primary">
                    <LineChart
                      :points="s.points.map((p) => p.amount)"
                      :labels="revenueLabels"
                    />
                  </div>
                </CardContent>
              </Card>
            </div>
            <p
              v-else
              class="text-sm text-muted-foreground"
            >
              {{ t('admin.state.empty') }}
            </p>
          </section>

          <!-- Non-cash (XTR / GIFT) — clearly separate, never folded into cash -->
          <section v-if="nonCashSeries.length">
            <h3 class="mb-2 text-sm font-medium text-muted-foreground">
              {{ t('admin.analytics.revenue.nonCash') }}
            </h3>
            <p class="mb-2 text-xs text-muted-foreground">
              {{ t('admin.analytics.revenue.nonCashCaveat') }}
            </p>
            <div class="grid gap-4 md:grid-cols-2">
              <Card
                v-for="s in nonCashSeries"
                :key="`${s.currency}-${s.provider}`"
              >
                <CardContent class="p-4">
                  <div class="mb-1 flex items-center justify-between">
                    <span class="text-sm font-medium">{{ s.currency }}</span>
                    <span class="text-xs text-muted-foreground">{{ s.provider }}</span>
                  </div>
                  <div class="text-2xl font-bold tracking-tight">
                    {{ seriesTotal(s.points).toLocaleString() }} {{ s.currency }}
                  </div>
                  <div class="mt-2 text-muted-foreground">
                    <LineChart
                      :points="s.points.map((p) => p.amount)"
                      :labels="revenueLabels"
                    />
                  </div>
                </CardContent>
              </Card>
            </div>
          </section>
        </div>
      </AdminStateBlock>
    </TabsContent>

    <!-- ════════════════ SUBSCRIPTIONS ════════════════ -->
    <TabsContent
      value="subscriptions"
      class="flex flex-col gap-4"
    >
      <!-- MRR + MoM growth (per currency, from active paid subs' product pricing) -->
      <AdminStateBlock
        :is-loading="mrr.isLoading.value"
        :error="mrr.error.value"
        :is-empty="isEmpty(mrr.data.value)"
        @retry="mrr.refetch()"
      >
        <section class="flex flex-col gap-3">
          <div class="flex items-baseline justify-between">
            <h3 class="text-sm font-medium text-muted-foreground">
              {{ t('admin.analytics.mrr.title') }}
            </h3>
            <span
              v-if="(mrr.data.value?.excluded ?? 0) > 0"
              class="text-xs text-muted-foreground"
            >
              {{ t('admin.analytics.mrr.excluded', { count: mrr.data.value?.excluded ?? 0 }) }}
            </span>
          </div>
          <div
            v-if="mrrRows.length"
            class="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4"
          >
            <StatCard
              v-for="row in mrrRows"
              :key="row.currency"
              :label="t('admin.analytics.mrr.label', { currency: row.currency })"
              :value="row.mrr"
              format="currency"
              :currency="row.currency"
              :delta-pct="row.growth_pct"
              :caveat="row.growth_pct === null ? t('admin.analytics.revenue.noPrior') : t('admin.analytics.mrr.caveat', { count: row.subscriptions })"
            />
          </div>
          <p
            v-else
            class="text-sm text-muted-foreground"
          >
            {{ t('admin.state.empty') }}
          </p>
        </section>
      </AdminStateBlock>

      <!-- Churn rate + net-new + active gift/paid split -->
      <AdminStateBlock
        :is-loading="subBreakdown.isLoading.value"
        :error="subBreakdown.error.value"
        :is-empty="isEmpty(subBreakdown.data.value)"
        @retry="subBreakdown.refetch()"
      >
        <section
          v-if="subBreakdown.data.value"
          class="flex flex-col gap-3"
        >
          <h3 class="text-sm font-medium text-muted-foreground">
            {{ t('admin.analytics.subscriptions.healthTitle') }}
          </h3>
          <div class="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
            <StatCard
              :label="t('admin.analytics.subscriptions.activePaid')"
              :value="subBreakdown.data.value.active_paid"
            />
            <StatCard
              :label="t('admin.analytics.subscriptions.activeGifted')"
              :value="subBreakdown.data.value.active_gifted"
              :caveat="t('admin.analytics.subscriptions.giftedCaveat')"
            />
            <StatCard
              :label="t('admin.analytics.subscriptions.churnRate')"
              :value="(subBreakdown.data.value.churn_rate ?? 0) / 100"
              format="percent"
              :caveat="subBreakdown.data.value.churn_rate === null
                ? t('admin.analytics.subscriptions.churnNoBase')
                : t('admin.analytics.subscriptions.churnCaveat', { days: subBreakdown.data.value.churn_period_days })"
            />
            <StatCard
              :label="t('admin.analytics.subscriptions.netNew')"
              :value="subBreakdown.data.value.net_new"
              :caveat="t('admin.analytics.subscriptions.netNewCaveat', { days: subBreakdown.data.value.churn_period_days })"
            />
            <StatCard
              :label="t('admin.analytics.subscriptions.gifted')"
              :value="subBreakdown.data.value.gifted"
            />
          </div>
        </section>
      </AdminStateBlock>

      <AdminStateBlock
        :is-loading="subTrend.isLoading.value"
        :error="subTrend.error.value"
        :is-empty="!subTrend.data.value?.points?.length"
        @retry="subTrend.refetch()"
      >
        <Card>
          <CardContent class="p-4">
            <h3 class="mb-3 text-sm font-medium text-muted-foreground">
              {{ t('admin.analytics.subscriptions.trend') }}
            </h3>
            <div class="grid gap-4 md:grid-cols-3">
              <div>
                <p class="mb-1 text-xs text-muted-foreground">
                  {{ t('admin.analytics.subscriptions.new') }}
                </p>
                <div class="text-green-600 dark:text-green-400">
                  <LineChart
                    :points="subNewSeries"
                    :labels="subTrendLabels"
                  />
                </div>
              </div>
              <div>
                <p class="mb-1 text-xs text-muted-foreground">
                  {{ t('admin.analytics.subscriptions.active') }}
                </p>
                <div class="text-primary">
                  <LineChart
                    :points="subActiveSeries"
                    :labels="subTrendLabels"
                  />
                </div>
              </div>
              <div>
                <p class="mb-1 text-xs text-muted-foreground">
                  {{ t('admin.analytics.subscriptions.ended') }}
                </p>
                <div class="text-red-600 dark:text-red-400">
                  <LineChart
                    :points="subEndedSeries"
                    :labels="subTrendLabels"
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </AdminStateBlock>

      <AdminStateBlock
        :is-loading="subBreakdown.isLoading.value"
        :error="subBreakdown.error.value"
        :is-empty="isEmpty(subBreakdown.data.value)"
        @retry="subBreakdown.refetch()"
      >
        <div class="grid gap-4 md:grid-cols-2">
          <Card>
            <CardContent class="p-4">
              <h3 class="mb-3 text-sm font-medium text-muted-foreground">
                {{ t('admin.analytics.subscriptions.byStatus') }}
              </h3>
              <div class="text-primary">
                <BarChart
                  :values="statusValues"
                  :labels="statusLabels"
                />
              </div>
              <div class="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                <span
                  v-for="row in statusRows"
                  :key="row.status"
                >{{ row.status }}: <strong class="text-foreground">{{ row.count }}</strong></span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent class="p-4">
              <h3 class="mb-3 text-sm font-medium text-muted-foreground">
                {{ t('admin.analytics.subscriptions.churn') }}
              </h3>
              <ul
                v-if="churnRows.length"
                class="space-y-1 text-sm"
              >
                <li
                  v-for="row in churnRows"
                  :key="row.reason"
                  class="flex items-center justify-between"
                >
                  <span class="text-muted-foreground">{{ row.reason }}</span>
                  <span class="font-medium">{{ row.count }}</span>
                </li>
              </ul>
              <p
                v-else
                class="text-sm text-muted-foreground"
              >
                {{ t('admin.state.empty') }}
              </p>
            </CardContent>
          </Card>
        </div>
      </AdminStateBlock>
    </TabsContent>
  </Tabs>
</template>
