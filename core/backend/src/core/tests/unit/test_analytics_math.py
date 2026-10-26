"""Pure parts of the admin money analytics: helpers, exact-currency pricing, the MRR fold."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from core.domain.products import product_price_in
from core.services.analytics import AnalyticsService, _clamp, _growth_pct, _week_start


@dataclass
class _Price:
    amount: float
    currency: str


@dataclass
class _Product:
    product_id: str
    duration_days: int
    recurring: bool = True
    prices: dict[str, _Price] = field(default_factory=dict)


class _SinglePriceProduct:
    """A product without a ``prices`` mapping: only ``get_price_for`` (falls back to its one currency)."""

    def __init__(self, price: _Price | None):
        self._price = price

    def get_price_for(self, currency: str) -> _Price:
        if self._price is None:
            raise StopIteration  # what next(iter({})) raises in a catalog without prices
        return self._price


class _Catalog:
    def __init__(self, *products: _Product):
        self._products = {p.product_id: p for p in products}

    def get_product(self, product_id: str):
        return self._products.get(product_id)


def _service(catalog) -> AnalyticsService:
    return AnalyticsService(None, None, SimpleNamespace(products=catalog), None)  # type: ignore[arg-type]


@pytest.mark.business_logic
class TestHelpers:
    def test_growth_none_when_prior_zero(self):
        assert _growth_pct(100.0, 0.0) is None
        assert _growth_pct(0.0, 0.0) is None

    def test_growth_computed_when_prior_nonzero(self):
        assert _growth_pct(150.0, 100.0) == 50.0
        assert _growth_pct(50.0, 100.0) == -50.0

    def test_clamp(self):
        assert _clamp(100_000, 1, 365) == 365
        assert _clamp(0, 1, 365) == 1
        assert _clamp(30, 1, 365) == 30

    def test_week_start_is_monday_midnight_utc(self):
        assert _week_start(datetime(2026, 9, 26, 15, 30, tzinfo=UTC)) == datetime(2026, 9, 21, tzinfo=UTC)
        assert _week_start(datetime(2026, 9, 21, 0, 0, tzinfo=UTC)) == datetime(2026, 9, 21, tzinfo=UTC)


@pytest.mark.business_logic
class TestProductPriceIn:
    def test_reads_the_prices_mapping(self):
        product = _Product("m", 30, prices={"RUB": _Price(555.0, "RUB")})

        assert product_price_in(product, "RUB") == _Price(555.0, "RUB")
        assert product_price_in(product, "USD") is None  # never another currency's price

    def test_without_a_mapping_keeps_get_price_for_only_in_the_same_currency(self):
        product = _SinglePriceProduct(_Price(5.0, "USD"))

        assert product_price_in(product, "USD") == _Price(5.0, "USD")  # type: ignore[arg-type]
        assert product_price_in(product, "RUB") is None  # type: ignore[arg-type]

    def test_no_price_at_all_is_none(self):
        assert product_price_in(_SinglePriceProduct(None), "RUB") is None  # type: ignore[arg-type]
        assert product_price_in(None, "RUB") is None


@pytest.mark.business_logic
class TestFoldMrr:
    def test_normalizes_to_a_month_and_excludes_what_it_cannot_price(self):
        catalog = _Catalog(
            _Product("MONTH", 30, prices={"RUB": _Price(555.0, "RUB")}),
            _Product("WEEK", 7, prices={"RUB": _Price(222.0, "RUB")}),
            _Product("ONCE", 30, recurring=False, prices={"RUB": _Price(99.0, "RUB")}),
            _Product("USD_ONLY", 30, prices={"USD": _Price(5.0, "USD")}),
        )
        rows = [
            {"product_id": "MONTH", "currency": "RUB", "count": 2},
            {"product_id": "WEEK", "currency": "RUB", "count": 1},
            {"product_id": "NOPE", "currency": "RUB", "count": 3},  # unknown product
            {"product_id": "ONCE", "currency": "RUB", "count": 4},  # not recurring
            {"product_id": "USD_ONLY", "currency": "RUB", "count": 5},  # no RUB price
        ]

        mrr, subs, excluded = _service(catalog)._fold_mrr(rows)

        assert mrr["RUB"] == pytest.approx(2 * 555.0 + 222.0 * (30 / 7))
        assert subs == {"RUB": 3}
        assert excluded == 3 + 4 + 5

    def test_without_a_catalog_everything_is_excluded(self):
        mrr, subs, excluded = _service(None)._fold_mrr([{"product_id": "MONTH", "currency": "RUB", "count": 2}])

        assert mrr == {}
        assert subs == {}
        assert excluded == 2
