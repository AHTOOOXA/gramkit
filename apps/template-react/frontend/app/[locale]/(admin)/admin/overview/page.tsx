'use client';

import { AlertTriangle } from 'lucide-react';
import { useTranslations } from 'next-intl';

import { deltaPct, groupOverviewCards } from '@/lib/admin/overview';
import { useAdminLabels } from '@/hooks/useAdminLabels';
import { AdminStateBlock } from '@/components/admin/AdminStateBlock';
import { StatCard } from '@/components/admin/StatCard';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { useAuth } from '@/hooks';
import { useGetStatisticsOverviewAdminStatisticsOverviewGet } from '@/src/gen/hooks/useGetStatisticsOverviewAdminStatisticsOverviewGet';

/**
 * Admin → Overview — the KPI snapshot on the first admin tab, from the core
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
 *
 * Port of template-vue's `AdminOverview.vue`.
 */
export default function AdminOverviewPage() {
  const t = useTranslations('admin');
  const { isAdminOrOwner } = useAuth();
  const { cardLabel, sectionLabel, caveatLabel } = useAdminLabels();

  const {
    data: stats,
    isLoading,
    error,
    refetch,
  } = useGetStatisticsOverviewAdminStatisticsOverviewGet({
    // Gate the request behind the role check so non-admins never fire it.
    query: { enabled: isAdminOrOwner, staleTime: 60 * 1000 },
  });

  const isEmpty = !isLoading && !error && !stats;

  const grid = 'grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4';
  const heading = 'mb-2 text-sm font-medium text-muted-foreground';

  return (
    <AdminStateBlock
      isLoading={isLoading}
      error={error}
      isEmpty={isEmpty}
      onRetry={() => void refetch()}
      loading={
        <div className={grid}>
          {Array.from({ length: 8 }, (_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
      }
    >
      {stats && (
        <div className="flex flex-col gap-6">
          {/* Degraded: the backend could not gather everything (`error` set, zeros returned). */}
          {stats.error && (
            <Alert className="border-yellow-500/40 bg-yellow-500/10">
              <AlertDescription className="flex items-center gap-2 text-yellow-700 dark:text-yellow-400">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                {t('overview.degraded')}
              </AlertDescription>
            </Alert>
          )}

          {/* Users */}
          <section>
            <h2 className={heading}>{t('overview.sections.users')}</h2>
            <div className={grid}>
              <StatCard
                label={t('overview.kpi.totalUsers')}
                value={stats.users.total}
              />
              <StatCard
                label={t('overview.kpi.newToday')}
                value={stats.users.new_today}
                deltaPct={deltaPct(
                  stats.users.new_today,
                  stats.users.new_prev_day
                )}
                caveat={t('overview.caveats.partialDay')}
              />
              <StatCard
                label={t('overview.kpi.newThisWeek')}
                value={stats.users.new_this_week}
                deltaPct={deltaPct(
                  stats.users.new_this_week,
                  stats.users.new_prev_week
                )}
                sparklinePoints={[
                  stats.users.new_this_month,
                  stats.users.new_this_week,
                  stats.users.new_today,
                ]}
              />
              <StatCard
                label={t('overview.kpi.newThisMonth')}
                value={stats.users.new_this_month}
                deltaPct={deltaPct(
                  stats.users.new_this_month,
                  stats.users.new_prev_month
                )}
              />
              <StatCard
                label={t('overview.kpi.dau')}
                value={stats.users.dau}
                caveat={t('overview.caveats.activeProxy')}
              />
              <StatCard
                label={t('overview.kpi.wau')}
                value={stats.users.wau}
                caveat={t('overview.caveats.activeProxy')}
              />
              <StatCard
                label={t('overview.kpi.mau')}
                value={stats.users.mau}
                caveat={t('overview.caveats.activeProxy')}
              />
            </div>
          </section>

          {/* App-registered cards, one group per section */}
          {groupOverviewCards(stats.cards).map((group) => (
            <section key={group.section}>
              <h2 className={heading}>{sectionLabel(group.section)}</h2>
              <div className={grid}>
                {group.cards.map((card) => (
                  <StatCard
                    key={card.key}
                    label={cardLabel(card)}
                    value={card.value}
                    deltaPct={
                      card.value === null
                        ? null
                        : deltaPct(card.value, card.previous)
                    }
                    sparklinePoints={card.sparkline}
                    format={card.format}
                    currency={card.currency ?? undefined}
                    caveat={card.caveat ? caveatLabel(card.caveat) : undefined}
                  />
                ))}
              </div>
            </section>
          ))}

          {/* Subscriptions */}
          <section>
            <h2 className={heading}>{t('overview.sections.subscriptions')}</h2>
            <div className={grid}>
              <StatCard
                label={t('overview.kpi.activeSubscribers')}
                value={stats.subscriptions.active_subscribers}
              />
            </div>
          </section>

          {/* Revenue (per currency, never summed) */}
          <section>
            <h2 className={heading}>{t('overview.sections.revenue')}</h2>
            {Object.keys(stats.revenue.alltime).length > 0 ? (
              <div className={grid}>
                {Object.entries(stats.revenue.alltime).map(
                  ([currency, amount]) => (
                    <StatCard
                      key={currency}
                      label={t('overview.kpi.revenueAlltime', { currency })}
                      value={amount}
                      format="currency"
                      currency={currency}
                    />
                  )
                )}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">
                {t('state.empty')}
              </p>
            )}
          </section>

          {/* Product sales (units per product) */}
          <section>
            <h2 className={heading}>{t('overview.sections.productSales')}</h2>
            {Object.keys(stats.product_sales.alltime).length > 0 ? (
              <div className={grid}>
                {Object.entries(stats.product_sales.alltime).map(
                  ([product, count]) => (
                    <StatCard
                      key={product}
                      label={t('overview.kpi.productSalesAlltime', { product })}
                      value={count}
                    />
                  )
                )}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">
                {t('state.empty')}
              </p>
            )}
          </section>
        </div>
      )}
    </AdminStateBlock>
  );
}
