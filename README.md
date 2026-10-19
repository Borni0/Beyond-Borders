# Beyond Borders — `finTech`

> Your global education journey starts with financial clarity.
>
> AI Financial Readiness & Cross-Border Finance Copilot for International Students.

This repository contains the Phase 1 foundation for Beyond Borders. The full
product specification is provided separately; this README documents only what
exists in code today.

---

## Phase 1 scope (what works right now)

- Monorepo structure: `apps/web` (Next.js) and `services/api` (FastAPI).
- Design system tokens (colors, type, spacing) per the spec.
- Authentication: register, sign in, sign out, forgot/reset password.
- Server-side authorization and ownership enforcement (Phase 1 exit condition).
- Sidebar navigation per the spec's authenticated app structure (other items
  are stubbed pages labeled "Coming in Phase N").
- Health probe, OpenAPI docs in dev, structured logging, CORS, secure cookies.
- Vitest + React Testing Library unit tests and Playwright end-to-end tests.
- GitHub Actions CI for lint, typecheck, and tests on both sides.

## Out of scope this phase

The following land in later phases per the spec roadmap:

- Phase 2 — study plans, costs, funding, financial calculation engine.
- Phase 3 — stress test engine, decision studio / destination comparison.
- Phase 4 — financial timeline, expense tracker, CSV import/export.
- Phase 5 — exchange-rate provider, source registry (this scaffold uses
  **manual entry only**).
- Phase 6 — AI finance copilot.
- Phase 7 — production hardening, deploys.

---

## Local development

### Prerequisites

- Node.js LTS (this repo tested on Node 24).
- npm.
- Python 3.10+ (3.11+ recommended per spec).
- Docker (for the local Postgres).
- Git.

### 1. Install dependencies

```bash
# Frontend (Next.js)
cd apps/web
npm install

# Backend (FastAPI)
cd ../../services/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Configure environment

```bash
# From repo root
cp .env.example .env
cp services/api/.env.example services/api/.env
cp apps/web/.env.example apps/web/.env.local
```

Edit the secret values. The defaults are safe for local development.

### 3. Start Postgres

> Important: in this environment, the compatible command is `docker-compose up -d db` instead of `docker compose up -d db`, because the installed Docker client is older than the compose plugin requirement.

```bash
docker-compose up -d db
```

### 4. Run database migrations

> Important: the Phase 1 migration in `services/api/alembic/versions/0002_phase1_readiness.py` must use PostgreSQL boolean defaults (`false`) instead of integer defaults (`0`); otherwise `alembic upgrade head` fails with a `DatatypeMismatch` when `is_one_time` and `is_refundable` are created.

```bash
cd services/api
source .venv/bin/activate
alembic upgrade head
```

### 5. Start the backend

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/api/v1/health` — should return `{"status":"ok"}`.
OpenAPI docs at `http://127.0.0.1:8000/docs` (dev only).

### 6. Start the frontend

In a separate terminal:

```bash
cd apps/web
npm run dev
```

Open `http://localhost:3000`.

### Important: server-only vs browser-safe API code

The Next.js App Router enforces a strict server/client split. Files that import `next/headers` or `cookies` are server-only and cannot be imported by client components. The frontend keeps the cookie-aware FastAPI bridge in `apps/web/lib/api.ts` for server-side pages and route handlers, while browser UI code uses `apps/web/lib/client-api.ts` and hits the same-origin `/api/*` proxies instead. If a module mixes both layers, the app throws the `next/headers` boundary error.

---

## Tests

```bash
# Backend
cd services/api
source .venv/bin/activate
pytest -q

# Frontend (unit + component)
cd ../../apps/web
npm test
npm run typecheck
npm run lint

# End-to-end
npm run e2e
```

The backend test suite includes `test_ownership.py`, which proves that one
user's session cookie cannot read another user's profile — the explicit Phase 1
exit condition.

---

## Repository layout

See `docs/architecture.md` for the full breakdown.

```
finTech/
├── apps/web/                  # Next.js App Router, TS strict
├── services/api/              # FastAPI, SQLAlchemy, Alembic
├── packages/shared-types/     # Cross-package TS/Zod types
├── docs/                      # Architecture, API, security
└── .github/workflows/         # CI
```

---

## Security notes

- Cookies are `HttpOnly`, `SameSite=Lax`, `Secure` (toggle via `COOKIE_SECURE`).
- Passwords are hashed with bcrypt (cost 12).
- Password reset returns 204 in all situations (no email enumeration).
- Reset tokens are single-use, 1-hour TTL, stored as hashes.
- CORS restricted to `FRONTEND_ORIGIN`.
- See `docs/security.md` for the full Phase 1 threat model.