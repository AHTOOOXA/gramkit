from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from core.infrastructure.config import settings
from core.infrastructure.database.models.payments import Payment
from core.infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CurrencyPrice:
    amount: float
    currency: str


async def default_reward(user_id: UUID, payment: Payment, recurring_details: dict, subscriptions_service) -> None:
    logger.warning(
        f"Default reward: payment {payment.id} for user {user_id} completed successfully (product {payment.product_id} has no reward handler)"
    )


async def weekly_reward(user_id: UUID, payment: Payment, recurring_details: dict, subscriptions_service) -> None:
    logger.info(f"Weekly reward: initiating top-up for user {user_id}, payment {payment.id}")
    await subscriptions_service.top_up_subscription(
        user_id,
        payment.product_id,
        7,
        payment,
        recurring_details,
    )


async def monthly_reward(user_id: UUID, payment: Payment, recurring_details: dict, subscriptions_service) -> None:
    logger.info(f"Monthly reward: initiating top-up for user {user_id}, payment {payment.id}")
    await subscriptions_service.top_up_subscription(
        user_id,
        payment.product_id,
        30,
        payment,
        recurring_details,
    )


async def yearly_reward(user_id: UUID, payment: Payment, recurring_details: dict, subscriptions_service) -> None:
    logger.info(f"Yearly reward: initiating top-up for user {user_id}, payment {payment.id}")
    await subscriptions_service.top_up_subscription(
        user_id,
        payment.product_id,
        365,
        payment,
        recurring_details,
    )


RewardStrategy = Callable[[UUID, Payment, dict[str, Any], Any], Awaitable[None]]


@dataclass
class PaymentProduct:
    product_id: str
    name: str
    duration_days: int
    prices: dict[str, CurrencyPrice]
    recurring: bool = False
    reward_handler: RewardStrategy = field(default=default_reward)

    def get_price_for(self, currency: str) -> CurrencyPrice:
        return self.prices.get(currency) or next(iter(self.prices.values()))

    async def reward(self, user_id: UUID, payment: Payment, recurring_details: dict, subscriptions_service) -> None:
        await self.reward_handler(user_id, payment, recurring_details, subscriptions_service)


# Legacy products (inactive - keeping for existing subscriptions)
LEGACY_PRODUCTS = {
    # V1 products
    "WEEK_SUB": PaymentProduct(
        product_id="WEEK_SUB",
        name="Weekly Subscription",
        duration_days=7,
        prices={"RUB": CurrencyPrice(129.0, "RUB"), "USD": CurrencyPrice(1.49, "USD")},
        recurring=True,
        reward_handler=weekly_reward,
    ),
    "MONTH_SUB": PaymentProduct(
        product_id="MONTH_SUB",
        name="Monthly Subscription",
        duration_days=30,
        prices={"RUB": CurrencyPrice(249.0, "RUB"), "USD": CurrencyPrice(2.99, "USD")},
        recurring=True,
        reward_handler=monthly_reward,
    ),
    "YEAR_SUB": PaymentProduct(
        product_id="YEAR_SUB",
        name="Yearly Subscription",
        duration_days=365,
        prices={"RUB": CurrencyPrice(749.0, "RUB"), "USD": CurrencyPrice(7.99, "USD")},
        recurring=True,
        reward_handler=yearly_reward,
    ),
    # V2 products (moved to legacy)
    "WEEK_SUB_V2": PaymentProduct(
        product_id="WEEK_SUB_V2",
        name="Weekly Subscription",
        duration_days=7,
        prices={"RUB": CurrencyPrice(169.0, "RUB"), "USD": CurrencyPrice(1.99, "USD")},
        recurring=True,
        reward_handler=weekly_reward,
    ),
    "MONTH_SUB_V2": PaymentProduct(
        product_id="MONTH_SUB_V2",
        name="Monthly Subscription",
        duration_days=30,
        prices={"RUB": CurrencyPrice(349.0, "RUB"), "USD": CurrencyPrice(3.99, "USD")},
        recurring=True,
        reward_handler=monthly_reward,
    ),
    "YEAR_SUB_V2": PaymentProduct(
        product_id="YEAR_SUB_V2",
        name="Yearly Subscription",
        duration_days=365,
        prices={"RUB": CurrencyPrice(849.0, "RUB"), "USD": CurrencyPrice(9.99, "USD")},
        recurring=True,
        reward_handler=yearly_reward,
    ),
}

# Active products with updated pricing
AVAILABLE_PRODUCTS = {
    "WEEK_SUB_V3": PaymentProduct(
        product_id="WEEK_SUB_V3",
        name="Weekly Subscription",
        duration_days=7,
        prices={"RUB": CurrencyPrice(222.0, "RUB"), "USD": CurrencyPrice(1.99, "USD")},
        recurring=True,
        reward_handler=weekly_reward,
    ),
    "MONTH_SUB_V3": PaymentProduct(
        product_id="MONTH_SUB_V3",
        name="Monthly Subscription",
        duration_days=30,
        prices={"RUB": CurrencyPrice(555.0, "RUB"), "USD": CurrencyPrice(3.99, "USD")},
        recurring=True,
        reward_handler=monthly_reward,
    ),
    "YEAR_SUB_V3": PaymentProduct(
        product_id="YEAR_SUB_V3",
        name="Yearly Subscription",
        duration_days=365,
        prices={"RUB": CurrencyPrice(999.0, "RUB"), "USD": CurrencyPrice(9.99, "USD")},
        recurring=True,
        reward_handler=yearly_reward,
    ),
}

# Test products for development (only available when debug=True)
TEST_PRODUCTS = {
    "TEST_ONETIME": PaymentProduct(
        product_id="TEST_ONETIME",
        name="Test One-time Payment",
        duration_days=7,
        prices={"XTR": CurrencyPrice(1.0, "XTR")},  # 1 Telegram Star
        recurring=False,
    ),
    "TEST_SUBSCRIPTION": PaymentProduct(
        product_id="TEST_SUBSCRIPTION",
        name="Test Subscription",
        duration_days=30,
        prices={"XTR": CurrencyPrice(1.0, "XTR")},  # 1 Telegram Star
        recurring=True,
        reward_handler=monthly_reward,
    ),
}

# Products shown in profile page (excludes test products)
CURRENT_OFFERS = AVAILABLE_PRODUCTS

# Combined dictionary for internal use (contains ALL products)
ALL_PRODUCTS = {**LEGACY_PRODUCTS, **AVAILABLE_PRODUCTS}


def get_product(product_id: str) -> PaymentProduct | None:
    """
    Get product by ID, checking both active and legacy products
    When debug mode is enabled, also includes test products

    Args:
        product_id: Product ID to look up

    Returns:
        PaymentProduct or None if not found
    """
    # Include test products in debug mode
    if settings.debug:
        all_products = {**ALL_PRODUCTS, **TEST_PRODUCTS}
        return all_products.get(product_id)

    return ALL_PRODUCTS.get(product_id)
