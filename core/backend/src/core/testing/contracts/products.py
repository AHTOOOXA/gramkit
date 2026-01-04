"""Base test class for Product Protocol contract tests.

Tests verify that the app's product catalog conforms to the
ProductCatalog protocol expected by core services.

The Protocol pattern enables:
- Core services to use app-specific products without importing app code
- Type-safe product operations across the core/app boundary
- Multiple apps to share core services with different product catalogs

Apps inherit this class and provide a `products_module` fixture.
"""

import pytest


class BaseProductProtocolTests:
    """Base class for ProductCatalog Protocol compliance tests.

    Apps must provide a `products_module` fixture that returns their
    app.domain.products module.
    """

    # =========================================================================
    # Protocol Compliance Tests
    # =========================================================================

    @pytest.mark.contract
    def test_has_available_products_attribute(self, products_module):
        """Product catalog exposes AVAILABLE_PRODUCTS dict."""
        assert hasattr(products_module, "AVAILABLE_PRODUCTS"), "Product catalog must expose AVAILABLE_PRODUCTS dict"
        assert isinstance(products_module.AVAILABLE_PRODUCTS, dict)
        assert len(products_module.AVAILABLE_PRODUCTS) > 0, "AVAILABLE_PRODUCTS must not be empty"

    @pytest.mark.contract
    def test_has_legacy_products_attribute(self, products_module):
        """Product catalog exposes LEGACY_PRODUCTS for existing subscriptions."""
        assert hasattr(products_module, "LEGACY_PRODUCTS"), (
            "Product catalog must expose LEGACY_PRODUCTS for backward compatibility"
        )
        assert isinstance(products_module.LEGACY_PRODUCTS, dict)

    @pytest.mark.contract
    def test_has_test_products_attribute(self, products_module):
        """Product catalog exposes TEST_PRODUCTS for development."""
        assert hasattr(products_module, "TEST_PRODUCTS"), "Product catalog must expose TEST_PRODUCTS for development"
        assert isinstance(products_module.TEST_PRODUCTS, dict)

    @pytest.mark.contract
    def test_has_get_product_function(self, products_module):
        """Product catalog exposes get_product() function."""
        assert hasattr(products_module, "get_product"), "Product catalog must expose get_product() function"
        assert callable(products_module.get_product)

    # =========================================================================
    # Product Structure Tests
    # =========================================================================

    @pytest.mark.contract
    def test_get_product_returns_valid_product(self, products_module):
        """get_product() returns product with correct structure."""
        product_id = list(products_module.AVAILABLE_PRODUCTS.keys())[0]
        product = products_module.get_product(product_id)

        assert product is not None, f"Product {product_id} should exist"

    @pytest.mark.contract
    def test_product_has_required_fields(self, products_module):
        """Product has all required fields for Protocol compliance."""
        product_id = list(products_module.AVAILABLE_PRODUCTS.keys())[0]
        product = products_module.get_product(product_id)

        assert hasattr(product, "product_id"), "Product missing product_id"
        assert hasattr(product, "name"), "Product missing name"
        assert hasattr(product, "duration_days"), "Product missing duration_days"
        assert hasattr(product, "prices"), "Product missing prices"
        assert hasattr(product, "recurring"), "Product missing recurring"
        assert hasattr(product, "reward_handler"), "Product missing reward_handler"

    @pytest.mark.contract
    def test_product_id_matches_key(self, products_module):
        """Product ID matches dictionary key."""
        for key, product in products_module.AVAILABLE_PRODUCTS.items():
            assert product.product_id == key, f"Product ID mismatch: key={key}, product_id={product.product_id}"

    @pytest.mark.contract
    def test_product_duration_days_positive(self, products_module):
        """All products have positive duration_days."""
        all_products = {
            **products_module.AVAILABLE_PRODUCTS,
            **products_module.LEGACY_PRODUCTS,
            **products_module.TEST_PRODUCTS,
        }
        for product_id, product in all_products.items():
            assert product.duration_days > 0, f"Product {product_id} has invalid duration_days: {product.duration_days}"

    # =========================================================================
    # Product Pricing Tests
    # =========================================================================

    @pytest.mark.contract
    def test_product_prices_not_empty(self, products_module):
        """All products have at least one price."""
        for product_id, product in products_module.AVAILABLE_PRODUCTS.items():
            assert len(product.prices) > 0, f"Product {product_id} has no prices"

    @pytest.mark.contract
    def test_product_prices_structure(self, products_module):
        """Product prices conform to CurrencyPrice structure."""
        for product_id, product in products_module.AVAILABLE_PRODUCTS.items():
            for currency, price in product.prices.items():
                assert hasattr(price, "amount"), f"Product {product_id} price missing amount"
                assert hasattr(price, "currency"), f"Product {product_id} price missing currency"

    @pytest.mark.contract
    def test_product_prices_positive(self, products_module):
        """All product prices are positive."""
        all_products = {
            **products_module.AVAILABLE_PRODUCTS,
            **products_module.LEGACY_PRODUCTS,
            **products_module.TEST_PRODUCTS,
        }
        for product_id, product in all_products.items():
            for currency, price in product.prices.items():
                assert price.amount > 0, f"Product {product_id} has invalid price for {currency}: {price.amount}"

    @pytest.mark.contract
    def test_product_get_price_for_returns_price(self, products_module):
        """get_price_for() returns CurrencyPrice."""
        product = list(products_module.AVAILABLE_PRODUCTS.values())[0]
        price = product.get_price_for("RUB")

        assert price is not None
        assert price.amount > 0

    @pytest.mark.contract
    def test_product_get_price_for_fallback(self, products_module):
        """get_price_for() falls back to first available currency."""
        product = list(products_module.AVAILABLE_PRODUCTS.values())[0]
        price = product.get_price_for("NON_EXISTENT_CURRENCY")

        # Should return first available price
        assert price is not None, "Should fallback to first available price"

    # =========================================================================
    # Product Reward Tests
    # =========================================================================

    @pytest.mark.contract
    def test_product_has_reward_method(self, products_module):
        """Product implements reward() method."""
        product = list(products_module.AVAILABLE_PRODUCTS.values())[0]
        assert hasattr(product, "reward"), "Product missing reward method"
        assert callable(product.reward), "reward must be callable"

    @pytest.mark.contract
    def test_product_has_reward_handler(self, products_module):
        """Product has reward_handler callable."""
        for product_id, product in products_module.AVAILABLE_PRODUCTS.items():
            assert product.reward_handler is not None, f"Product {product_id} missing reward_handler"
            assert callable(product.reward_handler), f"Product {product_id} reward_handler not callable"

    # =========================================================================
    # get_product() Function Tests
    # =========================================================================

    @pytest.mark.contract
    def test_get_product_returns_active_product(self, products_module):
        """get_product() returns active products."""
        for product_id in products_module.AVAILABLE_PRODUCTS.keys():
            product = products_module.get_product(product_id)
            assert product is not None, f"Should find active product {product_id}"

    @pytest.mark.contract
    def test_get_product_returns_legacy_product(self, products_module):
        """get_product() returns legacy products for existing subscriptions."""
        for product_id in products_module.LEGACY_PRODUCTS.keys():
            product = products_module.get_product(product_id)
            assert product is not None, f"Should find legacy product {product_id}"

    @pytest.mark.contract
    def test_get_product_returns_none_for_unknown(self, products_module):
        """get_product() returns None for unknown product ID."""
        product = products_module.get_product("UNKNOWN_PRODUCT_ID_12345")
        assert product is None, "Should return None for unknown product"

    # =========================================================================
    # Subscription Product Tests
    # =========================================================================

    @pytest.mark.contract
    def test_subscription_products_have_recurring_flag(self, products_module):
        """Subscription products have recurring=True."""
        for product_id, product in products_module.AVAILABLE_PRODUCTS.items():
            if "SUB" in product_id:
                assert product.recurring is True, f"Subscription product {product_id} should have recurring=True"

    @pytest.mark.contract
    def test_subscription_products_have_valid_duration(self, products_module):
        """Subscription products have standard durations."""
        valid_durations = [7, 30, 365]  # week, month, year
        for product_id, product in products_module.AVAILABLE_PRODUCTS.items():
            if "SUB" in product_id:
                assert product.duration_days in valid_durations, (
                    f"Product {product_id} has non-standard duration: {product.duration_days}"
                )
