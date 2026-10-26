"""Product domain interface.

Defines the contract that app-specific product implementations must satisfy.
Uses Protocol for structural subtyping - no inheritance required.
"""

from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Protocol
from uuid import UUID


class CurrencyPrice(Protocol):
    """Protocol for product price in a specific currency."""

    amount: float
    currency: str


class PaymentProduct(Protocol):
    """Protocol for payment product definition.

    Apps must implement products that satisfy this interface.
    """

    product_id: str
    name: str
    duration_days: int
    recurring: bool

    def get_price_for(self, currency: str) -> CurrencyPrice:
        """Get price for specific currency."""
        ...

    async def reward(self, user_id: UUID, payment: Any, recurring_details: dict, subscriptions_service: Any) -> None:
        """Execute reward logic after successful payment."""
        ...


# Optional product members. They aren't on PaymentProduct, so a product without them still satisfies
# it; core reads them only through these accessors (one place, typed):
#   invoice_text(locale) -> (title, description) | None   the Telegram Stars invoice wording
#   daily_purchase_limit: int | None                       purchases per user per 24 h, shared by all
#                                                          limited products
#   async take_back(payment, subscriptions_service) -> str | None
#                                                          what a refund takes back (returns the note
#                                                          for the owner); None = the subscription period
#   prices: Mapping[str, CurrencyPrice]                    price per currency; admin MRR prices a
#                                                          subscription only in its own currency


def product_invoice_text(product: PaymentProduct | None, locale: str | None) -> tuple[str, str] | None:
    invoice_text: Callable[[str | None], tuple[str, str] | None] | None = getattr(product, "invoice_text", None)
    return invoice_text(locale) if invoice_text is not None else None


def product_daily_purchase_limit(product: PaymentProduct | None) -> int | None:
    limit: int | None = getattr(product, "daily_purchase_limit", None)
    return limit


async def product_take_back(product: PaymentProduct | None, payment: Any, subscriptions_service: Any) -> str | None:
    take_back: Callable[[Any, Any], Awaitable[str | None]] | None = getattr(product, "take_back", None)
    return await take_back(payment, subscriptions_service) if take_back is not None else None


def product_price_in(product: PaymentProduct | None, currency: str) -> CurrencyPrice | None:
    """Price in exactly ``currency`` — never ``get_price_for()``'s fallback to another currency.

    MRR must not price a RUB subscription with a USD price. Reads the optional ``prices`` mapping
    (currency -> price) when the product has one; otherwise asks ``get_price_for`` and keeps the
    answer only when it is in ``currency``. ``None`` when there is no such price.
    """
    if product is None:
        return None
    prices = getattr(product, "prices", None)
    if isinstance(prices, Mapping):
        price: CurrencyPrice | None = prices.get(currency)
        return price
    try:
        fallback = product.get_price_for(currency)
    except Exception:  # e.g. StopIteration from next(iter({})) on a product without prices
        return None
    return fallback if fallback is not None and getattr(fallback, "currency", None) == currency else None


class ProductCatalog(Protocol):
    """Protocol for app-specific product catalog.

    Core services depend on this interface. Apps must provide implementations
    of get_product(), AVAILABLE_PRODUCTS, CURRENT_OFFERS, and TEST_PRODUCTS.

    Example implementation:
        # app/domain/products.py
        from dataclasses import dataclass

        @dataclass
        class CurrencyPrice:
            amount: float
            currency: str

        @dataclass
        class PaymentProduct:
            product_id: str
            name: str
            duration_days: int
            prices: dict[str, CurrencyPrice]
            recurring: bool = False

            def get_price_for(self, currency: str) -> CurrencyPrice:
                return self.prices.get(currency) or next(iter(self.prices.values()))

            async def reward(self, user_id, payment, recurring_details, subscriptions_service):
                # Custom reward logic
                pass

        AVAILABLE_PRODUCTS = {...}
        CURRENT_OFFERS = {...}
        TEST_PRODUCTS = {...}

        def get_product(product_id: str) -> PaymentProduct | None:
            return AVAILABLE_PRODUCTS.get(product_id)
    """

    AVAILABLE_PRODUCTS: dict[str, PaymentProduct]
    """All available products (active + legacy). Includes test products in debug mode."""

    CURRENT_OFFERS: dict[str, PaymentProduct]
    """Products shown in profile page. Excludes test products."""

    TEST_PRODUCTS: dict[str, PaymentProduct]
    """Test products for development (only available in debug mode)."""

    def get_product(self, product_id: str) -> PaymentProduct | None:
        """Get product by ID.

        Args:
            product_id: Product identifier

        Returns:
            Product if found, None otherwise
        """
        ...
