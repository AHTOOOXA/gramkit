"""Product domain interface.

Defines the contract that app-specific product implementations must satisfy.
Uses Protocol for structural subtyping - no inheritance required.
"""

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
