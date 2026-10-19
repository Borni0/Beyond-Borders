# Architecture — Phase 1 + Phase 2

Beyond Borders is a TypeScript / Python monorepo with three top-level
concerns:

- `apps/web` — the Next.js 15 (App Router) frontend.
- `services/api` — the FastAPI backend with SQLAlchemy + Alembic.
- `packages/shared-types` — Zod schemas + TypeScript types shared between
  the frontend and any future SDKs.

## Why this layout

The spec recommends a monorepo with these logical concerns separated. We
follow that structure so the frontend, backend, and shared types can evolve
independently while still living in one repository.

```
Browser
   │
   ▼
Next.js UI  (apps/web)
   │
   ▼  server-side fetch (preserves cookies)
FastAPI  (services/api)
   │
   ▼
PostgreSQL  (docker compose "db")
```

## Auth

The backend owns authentication. It issues a session cookie
(`bb_session`, `HttpOnly`, `SameSite=Lax`, `Secure` in production) signed with
`itsdangerous`. Sessions are persisted in the `sessions` table so they can be
revoked server-side.

The frontend is stateless. Server components and route handlers call the
backend via `lib/api.ts`, which reads the cookie from the incoming request
and forwards it. Client components submit forms through a Next.js route
handler (`app/api/auth/[...]/route.ts`) that proxies the call to the backend,
so the cookie is set on the API origin and forwarded to the browser.

This satisfies spec §13's session-handling rules and the `/api/v1/auth/*`
endpoint contract from spec §8.

## Authorization

`get_current_user` in `app/core/deps.py` is the only path to a user object
inside request handlers. It looks up the session, fetches the user, and 401s
otherwise. Resources are always queried with `user_id` filters applied at the
repository layer; `test_ownership.py` proves that a session belonging to user
A cannot read or modify user B's records.

## Configuration

- Backend reads `services/api/.env` via `pydantic-settings`. Required keys:
  `DATABASE_URL`, `SECRET_KEY`, `FRONTEND_ORIGIN`, `SESSION_TTL_HOURS`,
  `COOKIE_SECURE`, `LOG_LEVEL`.
- Frontend reads `apps/web/.env.local`. Required: `NEXT_PUBLIC_API_BASE_URL`.

`.env.example` files are committed. Real `.env*` files are gitignored.

## Database

PostgreSQL 16 (via `docker-compose.yml`). After Phase 2 the schema covers:

- `users` — profile and credentials.
- `sessions` — server-side session records.
- `study_plans`, `cost_items`, `funding_sources` — the financial-readiness
  data (Phase 1).
- `data_sources`, `exchange_rates` — reference registry and FX table
  (Phase 1).
- `payment_events`, `savings_goals` — operational bills and savings
  targets (Phase 2).

Alembic manages schema changes. The current head is
`0003_phase2_payments`.

## Layered responsibilities

- **Frontend**: rendering, forms, client-side validation feedback, charts
  (Phase 2+), API calls, loading/empty/error states.
- **Backend**: auth, validation, business logic, financial calculations
  (Phase 1: readiness; Phase 2: timeline projection, savings rollup,
  conversion + transfer-fee math), AI tool orchestration (Phase 6+),
  external providers (Phase 5+).
- **Database**: persistent user, study-plan, funding, and payment records.
- **External services**: none yet. Future phases add an exchange-rate
  provider, an LLM provider, and possibly a notification or document store.

## Why "manual entry only" in Phase 1

The spec lists FX and LLM integrations as separate later phases. Wiring them
in early would require placeholder API keys, fake data, and additional
adapter infrastructure that adds no value until business features need it.
The financial calculator will use user-entered amounts until Phase 5 wires
in real rate providers.