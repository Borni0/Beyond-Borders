"""Tests for currency conversion using a user-provided FX table.

Lock the contract: identity rate is implicit, inverse pair is reciprocal,
missing pair raises (never silent 1:1), non-positive rate raises.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.services.financial.currency import (
    CurrencyError,
    convert,
    index_rates,
)
from app.services.financial.types import FxRate, RateType


def _rate(base: str, quote: str, rate: str) -> FxRate:
    return FxRate(
        base_currency=base,
        quote_currency=quote,
        rate=Decimal(rate),
        rate_type=RateType.REFERENCE,
        observed_at=date(2026, 1, 1),
    )


class TestIndexRates:
    def test_index_by_base_quote(self) -> None:
        table = index_rates(
            [_rate("USD", "EUR", "0.9"), _rate("USD", "GBP", "0.8")]
        )
        assert ("USD", "EUR") in table
        assert ("USD", "GBP") in table
        assert ("EUR", "USD") not in table  # direction matters

    def test_later_overwrites_earlier(self) -> None:
        # Two rates for the same pair → the second one wins. This lets the
        # caller re-stamp a rate without rebuilding the table.
        table = index_rates(
            [
                _rate("USD", "EUR", "0.9"),
                _rate("USD", "EUR", "0.95"),
            ]
        )
        assert table[("USD", "EUR")].rate == Decimal("0.95")


class TestConvert:
    def test_identity_when_same_currency(self) -> None:
        # No rate needed; identity is implicit and 1:1.
        out = convert(Decimal("100.00"), "USD", "USD", {})
        assert out == Decimal("100.00")

    def test_identity_is_case_insensitive(self) -> None:
        out = convert(Decimal("100.00"), "usd", "USD", {})
        assert out == Decimal("100.00")

    def test_direct_pair(self) -> None:
        table = index_rates([_rate("USD", "EUR", "0.9")])
        out = convert(Decimal("100"), "USD", "EUR", table)
        # 100 * 0.9 = 90.00 EUR.
        assert out == Decimal("90.00")

    def test_inverse_pair(self) -> None:
        # Only EUR→USD supplied; we should still be able to convert USD→EUR.
        table = index_rates([_rate("EUR", "USD", "1.1")])
        out = convert(Decimal("100"), "USD", "EUR", table)
        # 100 / 1.1 = 90.909... → rounded to 2 dp = 90.91.
        assert out == Decimal("90.91")

    def test_jpy_zero_decimal(self) -> None:
        table = index_rates([_rate("USD", "JPY", "150")])
        # 10 USD * 150 = 1500 JPY (integer).
        out = convert(Decimal("10.00"), "USD", "JPY", table)
        assert out == Decimal("1500")

    def test_missing_pair_raises(self) -> None:
        table = index_rates([_rate("USD", "EUR", "0.9")])
        with pytest.raises(CurrencyError):
            convert(Decimal("100"), "USD", "GBP", table)

    def test_non_positive_direct_rate_raises(self) -> None:
        table = index_rates([_rate("USD", "EUR", "0")])
        with pytest.raises(CurrencyError):
            convert(Decimal("100"), "USD", "EUR", table)

    def test_non_positive_inverse_rate_raises(self) -> None:
        table = index_rates([_rate("EUR", "USD", "-1.1")])
        with pytest.raises(CurrencyError):
            convert(Decimal("100"), "USD", "EUR", table)

    def test_negative_amount_raises(self) -> None:
        # Refusing to convert a negative is a safety net; the higher-level
        # inputs should never produce one.
        with pytest.raises(CurrencyError):
            convert(Decimal("-1"), "USD", "USD", {})

    def test_chain_through_table(self) -> None:
        # USD→EUR→GBP: caller supplies both pairs, engine should walk them.
        table = index_rates(
            [
                _rate("USD", "EUR", "0.9"),
                _rate("EUR", "GBP", "0.8"),
            ]
        )
        # This test only exercises single-hop (which is the spec). For multi-
        # hop the engine would need a path resolver; we just confirm the
        # single-hop behavior is correct so the contract is clear.
        out = convert(Decimal("100"), "USD", "EUR", table)
        assert out == Decimal("90.00")
