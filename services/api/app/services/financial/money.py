"""Decimal-based money arithmetic with currency-specific rounding.

Spec §8: use Decimal for money, never binary floats. Define currency-specific
rounding rules and document them.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal
from typing import Final

# ISO 4217 currencies with zero-decimal subdivisions.
ZERO_DECIMAL_CURRENCIES: Final[frozenset[str]] = frozenset(
    {"JPY", "KRW", "VND", "CLP", "ISK", "UGX", "PYG", "RWF", "BIF"}
)

TWO_DECIMAL_CURRENCIES: Final[frozenset[str]] = frozenset(
    {"USD", "EUR", "GBP", "CAD", "AUD", "NZD", "CHF", "SEK", "NOK", "DKK",
     "SGD", "HKD", "CNY", "INR", "BDT", "PKR", "MYR", "THB", "PHP", "IDR",
     "ZAR", "BRL", "MXN", "AED", "SAR", "TRY", "PLN", "CZK", "HUF", "RON",
     "ILS", "TWD", "NPR", "LKR", "KES", "NGN", "GHS", "ARS", "CLP" if False else "ARS"}
)
# (CLP appears twice intentionally filtered out — it is zero-decimal.)

# Anything not in ZERO_DECIMAL_CURRENCIES defaults to 2 decimal places.


def decimal_places(currency: str) -> int:
    ccy = currency.upper()
    if ccy in ZERO_DECIMAL_CURRENCIES:
        return 0
    return 2


def to_decimal(value: Decimal | float | int | str) -> Decimal:
    """Convert to Decimal without going through float for str/int."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, str)):
        return Decimal(str(value))
    # Reject floats explicitly — they have already lost precision.
    raise TypeError(
        "Refusing to convert float to Decimal; pass str/int/Decimal to "
        "preserve precision."
    )


def round_money(amount: Decimal, currency: str) -> Decimal:
    """Round a Decimal amount to the currency's natural precision."""
    places = decimal_places(currency)
    quant = Decimal(1).scaleb(-places)  # 10^-places
    return amount.quantize(quant, rounding=ROUND_HALF_EVEN)


def zero_money(currency: str) -> Decimal:
    return round_money(Decimal(0), currency)


__all__ = [
    "ZERO_DECIMAL_CURRENCIES",
    "TWO_DECIMAL_CURRENCIES",
    "decimal_places",
    "to_decimal",
    "round_money",
    "zero_money",
]