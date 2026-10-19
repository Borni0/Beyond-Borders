"""Currency conversion using a user-provided FX table.

Spec §8.4: store base, quote, rate, source, timestamp. Reject non-positive
rates and unsupported currency pairs.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from app.services.financial.money import round_money
from app.services.financial.types import FxRate


class CurrencyError(ValueError):
    """Raised when conversion is impossible (missing pair, non-positive rate)."""


def _table_key(base: str, quote: str) -> tuple[str, str]:
    return (base.upper(), quote.upper())


def index_rates(rates: Iterable[FxRate]) -> dict[tuple[str, str], FxRate]:
    """Index rates by (base, quote). Later entries overwrite earlier ones."""
    out: dict[tuple[str, str], FxRate] = {}
    for r in rates:
        key = _table_key(r.base_currency, r.quote_currency)
        out[key] = r
    return out


def _rate_for(
    table: dict[tuple[str, str], FxRate],
    base: str,
    quote: str,
) -> FxRate:
    if base.upper() == quote.upper():
        # Identity rate, not stored.
        from datetime import date

        return FxRate(
            base_currency=base.upper(),
            quote_currency=quote.upper(),
            rate=Decimal("1"),
            rate_type=__import__(
                "app.services.financial.types", fromlist=["RateType"]
            ).RateType.REFERENCE,
            observed_at=date(1970, 1, 1),
        )

    key = _table_key(base, quote)
    if key in table:
        return table[key]

    # Try the inverse pair.
    inv_key = _table_key(quote, base)
    if inv_key in table:
        inv = table[inv_key]
        if inv.rate <= 0:
            raise CurrencyError(f"Inverse rate for {base}/{quote} is non-positive.")
        inverted = FxRate(
            base_currency=base.upper(),
            quote_currency=quote.upper(),
            rate=(Decimal("1") / inv.rate),
            rate_type=inv.rate_type,
            observed_at=inv.observed_at,
        )
        return inverted

    raise CurrencyError(f"No FX rate available for {base}/{quote}.")


def convert(
    amount: Decimal,
    from_currency: str,
    to_currency: str,
    table: dict[tuple[str, str], FxRate],
) -> Decimal:
    """Convert `amount` from `from_currency` to `to_currency`.

    Uses Decimal throughout; rounds the result to `to_currency`'s precision.
    """
    if amount < 0:
        raise CurrencyError("Cannot convert a negative amount.")

    rate = _rate_for(table, from_currency, to_currency)
    if rate.rate <= 0:
        raise CurrencyError(f"Rate for {from_currency}/{to_currency} is non-positive.")
    converted = amount * rate.rate
    return round_money(converted, to_currency)


__all__ = ["CurrencyError", "index_rates", "convert"]