# API — Phase 1 + Phase 2

All endpoints live under `/api/v1`. JSON in, JSON out. Authentication is via
the `bb_session` cookie (sent automatically) or `Authorization: Bearer
<token>` (future).

## Conventions

### Error envelope

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Please review the highlighted inputs.",
    "details": {
      "field_name": "Reason."
    }
  }
}
```

| Status | `code` | Meaning |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Request body failed Pydantic validation. |
| 401 | `UNAUTHENTICATED` | Missing or invalid session. |
| 403 | `FORBIDDEN` | Authenticated but not allowed. |
| 404 | `NOT_FOUND` | Resource missing or hidden. |
| 409 | `CONFLICT` | Duplicate value (e.g. email). |
| 500 | `INTERNAL_ERROR` | Server fault. Details are redacted. |

### Timestamps

All timestamps are ISO 8601 in UTC.

## Endpoints

### `GET /api/v1/health`

Liveness probe. Always 200 unless the process is unhealthy.

```json
{ "status": "ok" }
```

### `POST /api/v1/auth/register`

Create an account.

Request:
```json
{
  "email": "student@example.com",
  "password": "correct-horse-battery-staple",
  "name": "Alex Student",
  "home_country": "BD",
  "home_currency": "USD",
  "display_currency": "USD"
}
```

Response 201: returns the public `User` object and sets the session cookie.

Errors:
- `409 CONFLICT` if the email is already registered.
- `400 VALIDATION_ERROR` if the password is too short or fields are missing.

### `POST /api/v1/auth/login`

Request:
```json
{ "email": "student@example.com", "password": "..." }
```

Response 200: public `User` and sets the session cookie.

Errors:
- `401 UNAUTHENTICATED` for any failure (does not differentiate "no such user"
  from "wrong password" to prevent enumeration).

### `POST /api/v1/auth/logout`

Revokes the current session and clears the cookie. Always 204.

### `POST /api/v1/auth/forgot-password`

Request:
```json
{ "email": "student@example.com" }
```

Response: 204 in all cases. In development, the reset token is logged to the
backend console. In production, an email would be sent (Phase 2+).

### `POST /api/v1/auth/reset-password`

Request:
```json
{ "token": "...", "new_password": "..." }
```

Response: 204. Errors: `400 VALIDATION_ERROR` (weak password) or
`401 UNAUTHENTICATED` (invalid/expired token).

### `GET /api/v1/users/me`

Returns the current user.

Response 200:
```json
{
  "id": "uuid",
  "email": "...",
  "name": "...",
  "home_country": "BD",
  "home_currency": "USD",
  "display_currency": "USD",
  "created_at": "...",
  "updated_at": "..."
}
```

### `PATCH /api/v1/users/me`

Update the current user. All fields optional.

Request:
```json
{
  "name": "New Name",
  "home_country": "DE",
  "home_currency": "EUR",
  "display_currency": "EUR"
}
```

Response 200: the updated user.

## OpenAPI

In development, the full OpenAPI schema is available at `/docs` (Swagger UI)
and `/redoc`. Production deploys should disable these (TODO in Phase 7).

---

## Study plans, costs, funding, FX, and readiness

All five entity groups follow the same shape: list / create / get /
update / delete. Every request requires an authenticated session.

### Study plans

- `GET    /api/v1/study-plans` — list the current user's plans.
- `POST   /api/v1/study-plans` — create. `end_date` is auto-computed.
- `GET    /api/v1/study-plans/{id}` — get one (404 if not yours).
- `PATCH  /api/v1/study-plans/{id}` — partial update.
- `DELETE /api/v1/study-plans/{id}` — 204; cascades costs + funding.

`POST` / `PATCH` also accept (all optional): `institution_name`,
`program_name`, `city`, `tuition_amount`, `tuition_currency`,
`home_currency`. Currency fields are upper-cased on the way through.

### Cost items (nested under a plan)

- `GET    /api/v1/plans/{plan_id}/costs`
- `POST   /api/v1/plans/{plan_id}/costs`
- `PATCH  /api/v1/plans/{plan_id}/costs/{id}`
- `DELETE /api/v1/plans/{plan_id}/costs/{id}`

Allowed `category` values: `tuition`, `accommodation`, `food`,
`transport`, `utilities`, `insurance`, `travel`, `visa`, `deposits`,
`study_materials`, `personal`, `miscellaneous`.

Allowed `frequency` values: `one_time`, `monthly`, `quarterly`,
`semester`, `annual`.

`due_before_departure` (bool, default `false`): when `true`, the cost
is always included in the upfront-cash projection, even if no
`start_date` is set. Use this for deposits you know you'll have to
pay before flying out.

### Funding sources (nested under a plan)

- `GET    /api/v1/plans/{plan_id}/funding`
- `POST   /api/v1/plans/{plan_id}/funding`
- `PATCH  /api/v1/plans/{plan_id}/funding/{id}`
- `DELETE /api/v1/plans/{plan_id}/funding/{id}`

`funding_type`: `savings`, `family`, `scholarship`, `loan`, `income`,
`other`. `status`: `confirmed`, `conditional`, `expected`,
`unavailable`.

### Data source registry (per-user, not per-plan)

- `GET    /api/v1/sources`
- `POST   /api/v1/sources`
- `PATCH  /api/v1/sources/{id}`
- `DELETE /api/v1/sources/{id}`

### Exchange rates (per-user, manual entry only)

- `GET  /api/v1/fx` — list your rates.
- `PUT  /api/v1/fx` — upsert by `(base_currency, quote_currency)`. A
  `Rate` is `{base_currency, quote_currency, rate (>0), rate_type,
  observed_at}`. The unique constraint guarantees one row per pair.
- `DELETE /api/v1/fx/{id}`

### Readiness (read-only snapshot)

- `GET /api/v1/plans/{plan_id}/readiness?upfront_window_days=30`

Returns the same shape the frontend consumes (no envelope):

```jsonc
{
  "plan_id": "...",
  "base_currency": "USD",
  "breakdown": {
    "base_currency": "USD",
    "per_year": [
      { "year_index": 1, "recurring_total": "...", "one_time_total": "...", "total": "..." }
    ],
    "first_year_cost": "...",
    "total_projected_cost": "...",
    "refundable_deposits": "...",
    "per_category": { "tuition": "...", "accommodation": "..." }
  },
  "funding": {
    "base_currency": "USD",
    "confirmed_total": "...",
    "conditional_total": "...",
    "expected_total": "...",
    "unavailable_total": "...",
    "eligible_confirmed": "...",
    "eligible_with_conditional": "...",
    "available_before_departure": "..."
  },
  "funding_gap": "...",
  "funding_surplus": "...",
  "upfront_cash_requirement": "...",
  "upfront_cash_gap": "...",
  "upfront_cash_window_days": 30,
  "statuses": ["funding_gap_identified", "conditional_funding", "scenario_sensitive"],
  "missing_inputs": ["No FX rate entered for USD/EUR."],
  "notes": ["Scenario sensitivity is not yet modeled."]
}
```

All money fields are **strings** of `Decimal` values. The frontend
parses them with `new Intl.NumberFormat` for display only; the engine
never rounds. See `docs/calculation.md` for the full rule set.

Phase 1 enrichment fields also returned alongside the headline numbers:

```jsonc
{
  ...
  "first_year_funding_gap": "...",     // gap restricted to year 1
  "coverage_pct": "...",               // eligible_with_conditional / total,
                                       // or null when there is no cost
  "potential_gap_after_expected": "..."  // how much the headline gap would
                                       // widen if every conditional /
                                       // expected source failed
}
```

---

## Phase 2 — Payment events, savings goals, funding-plan aggregate

### Payment events

CRUD on user-owned payment events. Events may optionally link to a study
plan via `plan_id` (nullable so "before-a-plan" payments like application
fees work).

```
GET    /api/v1/payments?plan_id=<uuid>     # list (optional plan filter)
POST   /api/v1/payments                    # create (201)
PATCH  /api/v1/payments/{event_id}         # partial update
DELETE /api/v1/payments/{event_id}         # 204 on success, 404 if not owned
```

Allowed stored `status` values: `planned | scheduled | paid | cancelled`.
`overdue` is a **display-only** state: at read time, the API returns
`display_status` of `overdue` for any non-paid, non-cancelled event with
a past `due_date`.

```jsonc
{
  "id": "...",
  "user_id": "...",
  "plan_id": "...",
  "title": "Tuition deposit",
  "category": "tuition",
  "amount": "1500.0000",
  "currency": "USD",
  "due_date": "2026-10-30",
  "display_status": "planned",   // planned | scheduled | paid | overdue | cancelled
  "notes": null,
  "is_recurring": false,
  "recurrence_frequency": null,  // monthly | quarterly | semester | annual
  "recurrence_end_date": null,
  "created_at": "...",
  "updated_at": "..."
}
```

### Savings goals

```
GET    /api/v1/savings-goals?plan_id=<uuid>
POST   /api/v1/savings-goals
PATCH  /api/v1/savings-goals/{goal_id}
DELETE /api/v1/savings-goals/{goal_id}
```

```jsonc
{
  "id": "...",
  "user_id": "...",
  "plan_id": "...",
  "name": "First year",
  "target_amount": "12000.0000",
  "current_amount": "2000.0000",
  "currency": "USD",
  "target_date": "2027-09-01",
  "notes": null,
  "created_at": "...",
  "updated_at": "..."
}
```

### Funding-plan aggregate

All three endpoints live under `/api/v1/plans/{plan_id}/funding-plan/*`
and require the calling user to own the plan.

```
GET  /api/v1/plans/{plan_id}/funding-plan/summary
GET  /api/v1/plans/{plan_id}/funding-plan/timeline
POST /api/v1/plans/{plan_id}/funding-plan/convert
GET  /api/v1/plans/{plan_id}/funding-plan/export.csv
```

#### `summary`

Per-currency rollups of funding sources and savings goals, plus upcoming
and overdue payment totals in the plan's `base_currency`.

```jsonc
{
  "plan_id": "...",
  "base_currency": "USD",
  "buckets": [
    {
      "currency": "USD",
      "total": "15000.0000",
      "confirmed": "10000.0000",
      "conditional": "5000.0000",
      "expected": "0.0000",
      "unavailable": "0.0000"
    }
  ],
  "savings_buckets": [
    { "currency": "USD", "target_total": "12000.0000", "current_total": "2000.0000" }
  ],
  "upcoming_payments": "1500.0000",
  "overdue_payments": "200.0000",
  "upcoming_payments_count": 1,
  "overdue_payments_count": 1,
  "payments_by_currency": { "USD": "1700.0000" },
  "notes": ["1 payment(s) are past due."]
}
```

The "upcoming" window defaults to 30 days and is configurable via
`?upcoming_window_days=N` (1–365).

#### `timeline`

Chronological list of every payment event the user owns (recurring
occurrences projected forward up to 12 months past the original due date).

```jsonc
{
  "plan_id": "...",
  "entries": [
    {
      "event_id": "...",
      "title": "Monthly rent",
      "category": "accommodation",
      "amount": "800.0000",
      "currency": "USD",
      "due_date": "2026-10-05",
      "display_status": "planned",
      "plan_id": "...",
      "is_recurring": true
    }
  ]
}
```

#### `convert`

Preview a one-shot currency conversion + flat transfer-fee estimate
using the user's stored FX rates.

```jsonc
// Request
{ "from_amount": "1000.00", "from_currency": "USD", "to_currency": "EUR", "fee_pct": null }

// Response
{
  "from_currency": "USD",
  "to_currency": "EUR",
  "from_amount": "1000.0000",
  "converted_amount": "900.0000",
  "fee_pct": "0.0100",
  "fee_amount": "9.0000",
  "total_cost": "909.0000",
  "rate_used": "0.90000000",
  "rate_type": "user_entered"
}
```

If `fee_pct` is omitted, the default `1%` is applied. If the user has no
rate for the requested pair (or its inverse), the response is still
returned — `rate_used` will be `1` and `rate_type` will be
`user_entered`, signalling to the UI that the user needs to enter a
rate.

#### `export.csv`

Streams a CSV of every payment linked to the plan, with a header row and
one row per stored event. Includes the derived `display_status` so
spreadsheet users can filter without re-implementing the overdue rule.