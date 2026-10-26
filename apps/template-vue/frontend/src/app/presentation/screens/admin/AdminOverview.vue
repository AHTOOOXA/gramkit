<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { AlertTriangle } from '@lucide/vue';
import { deltaPct, groupOverviewCards } from '@core/composables';
import { useAuth } from '@app/composables/useAuth';
import { useAdminLabels } from '@app/admin/useAdminLabels';
import { useGetStatisticsOverviewAdminStatisticsOverviewGet } from '@gen/hooks/useGetStatisticsOverviewAdminStatisticsOverviewGet';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import StatCard from '@app/presentation/components/admin/StatCard.vue';
import AdminStateBlock from '@app/presentation/components/admin/AdminStateBlock.vue';

/**
 * AdminOverview — the KPI snapshot on the first admin tab, from the core
 * `GET /admin/statistics/overview`.
 *
 * Users, subscriptions, revenue and product sales come from core. The groups
 * between Users and Subscriptions are the `cards` this app registers on the
 * server (`register_overview_card` in the backend's `services/admin_metrics.py`),
 * one group per card `section`. Card labels, section titles and caveats are the
 * `admin.overview.kpi.<key>` / `.sections.<section>` / `.caveats.<caveat>` i18n
 * keys, with the card's English `label` as the fallback.
 *
 * Deltas are current vs the previous window, computed here. Revenue is per
 * currency and never summed across currencies. Sparklines are coarse window
 * summaries (30d / 7d / today), not a daily series. When the backend could not
 * gather everything it sets `error` and returns zeros: a banner says so.
 */
const { t } = useI18n();
const { isAdminOrOwner } = useAuth();
const { cardLabel, sectionLabel, caveatLabel } = useAdminLabels();

const { data, isLoading, error, refetch } = useGetStatisticsOverviewAdminStatisticsOverviewGet({
  query: {
    // Gate the request behind the role check so non-admins never fire it.
    enabled: () => isAdminOrOwner.value,
    staleTime: 60 * 1000,
  },
});

const stats = computed(() => data.value);
const isDegraded = computed(() => !!stats.value?.error);
const isEmpty = computed(() => !isLoading.value && !error.value && !stats.value);

const usersSpark = computed(() => {
  const u = stats.value?.users;
  return u ? [u.new_this_month, u.new_this_week, u.new_today] : [];
});

const cardGroups = computed(() => groupOverviewCards(stats.value?.cards));

/** All-time revenue per currency (never summed across currencies). */
const revenueRows = computed(() =>
  Object.entries(stats.value?.revenue.alltime ?? {}).map(([currency, amount]) => ({ currency, amount })),
);

/** All-time units sold per product id. */
const productSalesRows = computed(() =>
  Object.entries(stats.value?.product_sales.alltime ?? {}).map(([product, count]) => ({ product, count })),
);

const GRID = 'grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4';
const HEADING = 'mb-2 text-sm font-medium text-muted-foreground';
</script>

<template>
  <AdminStateBlock
    :is-loading="isLoading"
    :error="error"
    :is-empty="isEmpty"
    @retry="refetch()"
  >
    <template #loading>
      <div :class="GRID">
        <Skeleton
          v-for="i in 8"
          :key="i"
          class="h-24 rounded-xl"
        />
      </div>
    </template>

    <div
      v-if="stats"
      class="flex flex-col gap-6"
    >
      <!-- Degraded: the backend could not gather everything (`error` set, zeros returned). -->
      <Alert
        v-if="isDegraded"
        class="border-yellow-500/40 bg-yellow-500/10"
      >
        <AlertDescription class="flex items-center gap-2 text-yellow-700 dark:text-yellow-400">
          <AlertTriangle class="h-4 w-4 shrink-0" />
          {{ t('admin.overview.degraded') }}
        </AlertDescription>
      </Alert>

      <!-- Users -->
      <section>
        <h2 :class="HEADING">{{ t('admin.overview.sections.users') }}</h2>
        <div :class="GRID">
          <StatCard
            :label="t('admin.overview.kpi.totalUsers')"
            :value="stats.users.total"
          />
          <StatCard
            :label="t('admin.overview.kpi.newToday')"
            :value="stats.users.new_today"
            :delta-pct="deltaPct(stats.users.new_today, stats.users.new_prev_day)"
            :caveat="t('admin.overview.caveats.partialDay')"
          />
          <StatCard
            :label="t('admin.overview.kpi.newThisWeek')"
            :value="stats.users.new_this_week"
            :delta-pct="deltaPct(stats.users.new_this_week, stats.users.new_prev_week)"
            :sparkline-points="usersSpark"
          />
          <StatCard
            :label="t('admin.overview.kpi.newThisMonth')"
            :value="stats.users.new_this_month"
            :delta-pct="deltaPct(stats.users.new_this_month, stats.users.new_prev_month)"
          />
          <StatCard
            :label="t('admin.overview.kpi.dau')"
            :value="stats.users.dau"
            :caveat="t('admin.overview.caveats.activeProxy')"
          />
          <StatCard
            :label="t('admin.overview.kpi.wau')"
            :value="stats.users.wau"
            :caveat="t('admin.overview.caveats.activeProxy')"
          />
          <StatCard
            :label="t('admin.overview.kpi.mau')"
            :value="stats.users.mau"
            :caveat="t('admin.overview.caveats.activeProxy')"
          />
        </div>
      </section>

      <!-- App-registered cards, one group per section -->
      <section
        v-for="group in cardGroups"
        :key="group.section"
      >
        <h2 :class="HEADING">{{ sectionLabel(group.section) }}</h2>
        <div :class="GRID">
          <StatCard
            v-for="card in group.cards"
            :key="card.key"
            :label="cardLabel(card)"
            :value="card.value"
            :delta-pct="card.value === null ? null : deltaPct(card.value, card.previous)"
            :sparkline-points="card.sparkline"
            :format="card.format"
            :currency="card.currency ?? undefined"
            :caveat="card.caveat ? caveatLabel(card.caveat) : undefined"
          />
        </div>
      </section>

      <!-- Subscriptions -->
      <section>
        <h2 :class="HEADING">{{ t('admin.overview.sections.subscriptions') }}</h2>
        <div :class="GRID">
          <StatCard
            :label="t('admin.overview.kpi.activeSubscribers')"
            :value="stats.subscriptions.active_subscribers"
          />
        </div>
      </section>

      <!-- Revenue (per currency, never summed) -->
      <section>
        <h2 :class="HEADING">{{ t('admin.overview.sections.revenue') }}</h2>
        <div
          v-if="revenueRows.length"
          :class="GRID"
        >
          <StatCard
            v-for="row in revenueRows"
            :key="row.currency"
            :label="t('admin.overview.kpi.revenueAlltime', { currency: row.currency })"
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
      </section>

      <!-- Product sales (units per product) -->
      <section>
        <h2 :class="HEADING">{{ t('admin.overview.sections.productSales') }}</h2>
        <div
          v-if="productSalesRows.length"
          :class="GRID"
        >
          <StatCard
            v-for="row in productSalesRows"
            :key="row.product"
            :label="t('admin.overview.kpi.productSalesAlltime', { product: row.product })"
            :value="row.count"
          />
        </div>
        <p
          v-else
          class="text-sm text-muted-foreground"
        >
          {{ t('admin.state.empty') }}
        </p>
      </section>
    </div>
  </AdminStateBlock>
</template>
