# Calculation engine

The Phase 1 calculation engine lives entirely in
`services/api/app/services/financial/`. It is a **pure** Python module:
no SQLAlchemy, no Pydantic, no FastAPI, no I/O. That means it can be
unit-tested with a single import and a few dataclass literals.

This document locks the calculation rules so frontend, backend, and
tests never disagree.

## Inputs (frozen dataclasses)

| Type            | Fields                                                                  |
|-----------------|-------------------------------------------------------------------------|
| `PlanContext`   | `id`, `name`, `base_currency`, `start_date`, `duration_months`          |
| `CostItem`      | `id`, `category`, `description`, `amount`, `currency`, `frequency`, `start_date`, `end_date`, `is_one_time`, `is_refundable` |
| `FundingSource` | `id`, `name`, `funding_type`, `amount`, `currency`, `status`, `expected_date`, `notes` |
| `FxRate`        | `base_currency`, `quote_currency`, `rate`, `rate_type`, `observed_at`   |

## Money rules (non-negotiable)

1. All money is `Decimal`. No `float` anywhere in the engine.
2. `Decimal` is constructed from `str` or `int` only.
3. Rounding is **ROUND_HALF_EVEN** (banker's rounding) to the target
   currency's natural precision.
4. Zero-decimal currencies (JPY, KRW, VND, CLP, ISK, UGX, PYG, RWF,
   BIF) round to 0 dp. All other currencies round to 2 dp.
5. Rounding happens **once at the per-year, per-category, and per-
   source boundaries**, not in inner loops, to avoid drift.

## Cost projection

For a `CostItem` with `is_one_time == True` (or `frequency ==
ONE_TIME`):

- Find the 1-based study year that contains the item's effective date
  (`start_date` if set, else `end_date`, else today).
- If the date is **before** the plan starts, route the item to year 1
  (it counts as part of the upfront window).
- If the date is at or after `plan.start_date + duration_months`,
  the item is dropped (out of the plan's timeline).
- Otherwise, attribute the full amount to that year.

For a recurring `CostItem`:

- Compute the number of applicable periods per study year using the
  table below. Partial years use the months that actually fall inside
  the plan.
- Multiply `amount` × `periods` and add to that year's
  `recurring_total`.

| Frequency  | Periods in a full year         | Periods in a 6-month partial year |
|------------|--------------------------------|-----------------------------------|
| `MONTHLY`  | 12                             | 6                                 |
| `QUARTERLY`| 4                              | 2                                 |
| `SEMESTER` | 1 (one charge per academic yr) | 1 (if months ≥ 6)                 |
| `ANNUAL`   | 1                              | 0                                 |

Refundable deposits:

- Tracked in a separate `refundable_deposits` bucket on
  `CostBreakdown`.
- **Never** count toward `total_projected_cost`.
- Surfaced as a `note` on the readiness result so the UI can mention
  them without inflating the number.

## Funding breakdown

| Field                          | Definition                                                         |
|--------------------------------|--------------------------------------------------------------------|
| `confirmed_total`              | Sum of `CONFIRMED` sources (converted to base).                   |
| `conditional_total`            | Sum of `CONDITIONAL` sources.                                      |
| `expected_total`               | Sum of `EXPECTED` sources.                                         |
| `unavailable_total`            | Sum of `UNAVAILABLE` sources.                                      |
| `eligible_confirmed`           | = `confirmed_total`.                                               |
| `eligible_with_conditional`    | = `confirmed_total` + `conditional_total`.                         |
| `available_before_departure`   | `CONFIRMED` (any date) + `EXPECTED` whose `expected_date` ≤ `plan.start_date`. |

## Gap and surplus

```
gap        = max(0, projected_total_cost - eligible_confirmed)
surplus    = max(0, eligible_confirmed - projected_total_cost)
upfront_req = sum of cost items whose effective date is within the
              30-day upfront window (refundable excluded)
upfront_gap = max(0, upfront_req - available_before_departure)
```

Both `gap` and `surplus` are reported. The UI shows a green check
when `gap == 0` and `surplus > 0`.

## FX conversion

- `convert(amount, from_ccy, to_ccy, table)`:
  1. If `from_ccy == to_ccy` → identity (1.0, no FX row needed).
  2. Else look up `(from_ccy, to_ccy)` in the table. If found, apply.
  3. Else look up `(to_ccy, from_ccy)`. If found, use `1 / rate`.
  4. Else raise `CurrencyError`. Never silently fall back to 1:1.
- Non-positive rates raise `CurrencyError` either directly or via
  the inverse.
- Negative amounts raise `CurrencyError` (defensive; should never
  happen in normal flow).

If the orchestrator catches a `CurrencyError`, the readiness result
returns zero amounts and surfaces the error message in
`missing_inputs`, plus the `NEEDS_MORE_INFORMATION` status flag.

## Status classification (spec §9 + Phase 1 extension)

A plan can carry **multiple** statuses simultaneously. They never
exclude each other.

| Code                     | Fires when                                                              |
|--------------------------|-------------------------------------------------------------------------|
| `NEEDS_MORE_INFORMATION` | No costs, no confirmed funding, or missing FX rate.                    |
| `FUNDING_GAP_IDENTIFIED` | `funding_gap > 0`.                                                      |
| `UPFRONT_CASH_GAP`       | `upfront_cash_gap > 0`.                                                 |
| `CONDITIONAL_FUNDING`    | Any source is `CONDITIONAL` or `EXPECTED`.                              |
| `NO_MODELED_SHORTFALL`   | Has at least one cost and one confirmed source, and both gaps are 0, and no missing inputs. |
| `SCENARIO_SENSITIVE`     | Always appended in Phase 1; the chip is muted until Phase 2.           |

## Reproducibility

For the same `plan`, `costs`, `sources`, and `rates`, the engine
returns a `ReadinessResult` that round-trips through
`to_dict() → JSON → to_dict()` without changing any field. Tests
assert this byte-stability (see
`app/tests/finance/test_readiness.py::TestDeterminism`).

The full-stack round trip is asserted in
`app/tests/api/test_persistence.py::test_full_round_trip`.
