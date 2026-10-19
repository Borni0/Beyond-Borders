"""Tests for Decimal-based money rounding rules.

Locks the contract: zero-decimal currencies round to 0 dp; everyone else rounds
to 2 dp with HALF_EVEN (banker's rounding) to avoid drift.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.financial.money import (
    decimal_places,
    round_money,
    to_decimal,
    zero_money,
    ZERO_DECIMAL_CURRENCIES,
)


class TestDecimalPlaces:
    def test_jpy_is_zero_decimal(self) -> None:
        assert decimal_places("JPY") == 0
        assert decimal_places("jpy") == 0  # case-insensitive

    def test_krw_is_zero_decimal(self) -> None:
        assert decimal_places("KRW") == 0

    def test_usd_is_two_decimal(self) -> None:
        assert decimal_places("USD") == 2
        assert decimal_places("usd") == 2

    def test_eur_is_two_decimal(self) -> None:
        assert decimal_places("EUR") == 2

    def test_unknown_defaults_to_two_decimal(self) -> None:
        # ISO 4217 default = 2 dp; we don't try to enumerate every code.
        assert decimal_places("XYZ") == 2

    def test_documented_zero_decimal_set_is_consistent(self) -> None:
        # Sanity: every entry in ZERO_DECIMAL_CURRENCIES is recognized as 0 dp.
        for ccy in ZERO_DECIMAL_CURRENCIES:
            assert decimal_places(ccy) == 0, ccy


class TestRoundMoney:
    def test_usd_rounds_half_even_up_at_half_cent(self) -> None:
        # 0.125 → banker's rounding → 0.12 (even).
        assert round_money(Decimal("0.125"), "USD") == Decimal("0.12")

    def test_usd_rounds_half_even_up_at_above_half_cent(self) -> None:
        # 0.135 → banker's rounding → 0.14 (even).
        assert round_money(Decimal("0.135"), "USD") == Decimal("0.14")

    def test_usd_rounds_normal_two_dp(self) -> None:
        assert round_money(Decimal("1.236"), "USD") == Decimal("1.24")
        assert round_money(Decimal("1.234"), "USD") == Decimal("1.23")

    def test_jpy_rounds_to_integer(self) -> None:
        # 1500.7 → 1501; 1499.5 → 1500 (even).
        assert round_money(Decimal("1500.7"), "JPY") == Decimal("1501")
        assert round_money(Decimal("1499.5"), "JPY") == Decimal("1500")

    def test_krw_rounds_to_integer(self) -> None:
        assert round_money(Decimal("1234567.89"), "KRW") == Decimal("1234568")

    def test_zero_is_zero(self) -> None:
        assert round_money(Decimal("0"), "USD") == Decimal("0.00")
        assert round_money(Decimal("0"), "JPY") == Decimal("0")

    def test_negative_rounds_symmetrically(self) -> None:
        # -0.125 → -0.12 (banker's even).
        assert round_money(Decimal("-0.125"), "USD") == Decimal("-0.12")

    def test_case_insensitive_currency(self) -> None:
        assert round_money(Decimal("1.236"), "usd") == Decimal("1.24")
        assert round_money(Decimal("1500.7"), "jpy") == Decimal("1501")

    def test_idempotent(self) -> None:
        # Rounding an already-rounded value is a no-op.
        v = round_money(Decimal("1.236"), "USD")
        assert round_money(v, "USD") == v


class TestToDecimal:
    def test_from_string(self) -> None:
        assert to_decimal("1.23") == Decimal("1.23")

    def test_from_int(self) -> None:
        assert to_decimal(5) == Decimal("5")

    def test_passthrough_decimal(self) -> None:
        d = Decimal("3.14")
        assert to_decimal(d) is d

    def test_rejects_float(self) -> None:
        with pytest.raises(TypeError):
            to_decimal(1.23)

    def test_large_string_preserved(self) -> None:
        # 30-digit string would lose precision in float.
        big = "1" * 30
        assert to_decimal(big) == Decimal(big)


class TestZeroMoney:
    def test_usd_zero(self) -> None:
        assert zero_money("USD") == Decimal("0.00")

    def test_jpy_zero(self) -> None:
        assert zero_money("JPY") == Decimal("0")

    def test_zero_money_usable_in_sums(self) -> None:
        # Adding zero_money to a value of the same currency should keep precision.
        total = zero_money("USD") + Decimal("10.00")
        assert total == Decimal("10.00")
