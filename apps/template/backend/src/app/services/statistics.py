"""Generic Statistics Service for gathering app usage metrics.

Extend this service with app-specific statistics as needed.
"""

from datetime import UTC, datetime, timedelta

from app.services.base import BaseService
from core.infrastructure.logging import get_logger

logger = get_logger(__name__)


class StatisticsService(BaseService):
    """Service for gathering and formatting app statistics.

    This provides basic user, subscription, and revenue statistics.
    Extend with app-specific metrics as needed.
    """

    async def get_daily_statistics(self) -> dict:
        """Get comprehensive daily statistics for admin reports."""
        now = datetime.now(UTC)

        # Calculate closest 2:00 UTC as today_start
        utc_now = now
        today_2am_utc = utc_now.replace(hour=2, minute=0, second=0, microsecond=0)

        # If current UTC time is before 2:00 AM, use yesterday's 2:00 AM
        if utc_now.hour < 2:
            today_start = today_2am_utc - timedelta(days=1)
        else:
            today_start = today_2am_utc

        today_end = now  # Current time
        week_ago_start = today_start - timedelta(days=7)
        month_ago_start = today_start - timedelta(days=30)

        today_str = today_start.strftime("%Y-%m-%d")

        try:
            # User statistics using repository methods
            total_users = await self.repo.users.get_users_count()
            new_users_today = await self.repo.users.get_new_users_count(today_start)
            new_users_this_week = await self.repo.users.get_new_users_count(week_ago_start)
            new_users_this_month = await self.repo.users.get_new_users_count(month_ago_start)
            daily_active_users = await self.repo.users.get_updated_users_count(today_start, today_end)
            weekly_active_users = await self.repo.users.get_updated_users_count(week_ago_start, today_end)
            monthly_active_users = await self.repo.users.get_updated_users_count(month_ago_start, today_end)

            # Revenue and product statistics using repository methods
            total_revenue = await self.repo.payments.get_total_revenue_by_currency()
            today_revenue = await self.repo.payments.get_revenue_by_all_currencies_and_date(today_start, today_end)
            total_product_sales = await self.repo.payments.get_product_sales_stats()
            today_product_sales = await self.repo.payments.get_product_sales_stats_by_date(today_start, today_end)

            # Subscription statistics using repository methods
            active_subscribers = await self.repo.subscriptions.get_active_subscribers_count()

            return {
                "date": today_str,
                "users": {
                    "total": total_users,
                    "new_today": new_users_today,
                    "new_this_week": new_users_this_week,
                    "new_this_month": new_users_this_month,
                    "dau": daily_active_users,
                    "wau": weekly_active_users,
                    "mau": monthly_active_users,
                },
                "revenue": {
                    "alltime": total_revenue,
                    "today": today_revenue,
                },
                "product_sales": {
                    "alltime": total_product_sales,
                    "today": today_product_sales,
                },
                "subscriptions": {
                    "active_subscribers": active_subscribers,
                },
            }
        except Exception as e:
            # Log the error and return empty stats
            logger.error(f"Error gathering statistics: {str(e)}", exc_info=True)
            return {
                "date": today_str,
                "error": f"Failed to gather statistics: {str(e)}",
                "users": {
                    "total": 0,
                    "new_today": 0,
                    "new_this_week": 0,
                    "new_this_month": 0,
                    "dau": 0,
                    "wau": 0,
                    "mau": 0,
                },
                "revenue": {"alltime": {}, "today": {}},
                "product_sales": {"alltime": {}, "today": {}},
                "subscriptions": {"active_subscribers": 0},
            }

    def format_statistics_message(self, stats: dict) -> str:
        """Format statistics into a readable message for admin broadcast."""
        if "error" in stats:
            return f"📊 DAILY STATISTICS ({stats['date']})\n\n❌ {stats['error']}"

        message = f"📊 DAILY STATISTICS ({stats['date']})\n\n"

        # Users section
        message += "👥 USERS:\n"
        message += f"  - Total: {stats['users']['total']:,}\n"
        message += f"  - MAU: {stats['users']['mau']:,}\n"
        message += f"  - WAU: {stats['users']['wau']:,}\n"
        message += f"  - DAU: {stats['users']['dau']:,}\n"
        message += f"  - NEW this month: {stats['users']['new_this_month']:,}\n"
        message += f"  - NEW this week: {stats['users']['new_this_week']:,}\n"
        message += f"  - NEW today: {stats['users']['new_today']:,}\n\n"

        # Subscriptions section
        message += "💎 SUBSCRIPTIONS:\n"
        message += f"  - Active subscribers: {stats['subscriptions']['active_subscribers']:,}\n\n"

        # Revenue section
        message += "💰 REVENUE:\n"
        message += "  - ALL-TIME:\n"
        if stats["revenue"]["alltime"]:
            for currency, amount in stats["revenue"]["alltime"].items():
                message += f"    - {amount:.2f} {currency}\n"
        else:
            message += "    - 0\n"

        message += "  - TODAY:\n"
        if stats["revenue"]["today"]:
            for currency, amount in stats["revenue"]["today"].items():
                message += f"    - {amount:.2f} {currency}\n"
        else:
            message += "    - 0\n"

        message += "\n"

        # Product sales section
        message += "🛒 PRODUCT SALES:\n"
        message += "  - ALL-TIME:\n"
        if stats["product_sales"]["alltime"]:
            for product_id, count in stats["product_sales"]["alltime"].items():
                message += f"    - {product_id}: {count:,} sold\n"
        else:
            message += "    - No sales yet\n"

        message += "  - TODAY:\n"
        if stats["product_sales"]["today"]:
            for product_id, count in stats["product_sales"]["today"].items():
                message += f"    - {product_id}: {count:,} sold\n"
        else:
            message += "    - No sales today\n"

        # Add app-specific sections here as needed
        # Example:
        # message += "\n🎯 APP-SPECIFIC METRICS:\n"
        # message += f"  - Custom metric: {stats.get('custom_metric', 0):,}\n"

        return message
