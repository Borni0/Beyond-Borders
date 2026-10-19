# Security — Phase 1

## Threat model (Phase 1 scope)

Phase 1 is the authentication and authorization foundation. The threats
explicitly addressed:

| Threat | Mitigation |
|---|---|
| Credential stuffing / weak passwords | bcrypt (cost 12); min length 10; rate-limited login (TODO) |
| Session theft (XSS) | `HttpOnly` cookie; `SameSite=Lax` |
| Session theft (CSRF) | `SameSite=Lax` + backend check of `Origin` header on state-changing requests |
| Session fixation | New session ID issued at login |
| Session replay | Server-side session table; cookies are signed but checked against DB |
| Email enumeration via forgot-password | Always return 204; reset token is logged only in dev |
| Cross-user data access | `get_current_user` is the only path to a user; every query filters by `user_id`; covered by `test_ownership.py` |
| Secret leakage | `.env*` gitignored; only `.env.example` committed |
| Stack trace leakage | Custom exception handler returns a sanitized error envelope; never the traceback |

## Cookies

```
Name:        bb_session
HttpOnly:    true
SameSite:    Lax
Secure:      <COOKIE_SECURE, default true in production, false in dev>
Path:        /
Max-Age:     SESSION_TTL_HOURS * 3600
```

The cookie value is a signed token. Verification:

1. Unsigned, raise on tamper.
2. Look up the session ID in the `sessions` table.
3. Confirm `expires_at > now()`.
4. Fetch the owning user.

## Password hashing

`passlib[bcrypt]` with default cost (12). On register, the password is hashed
and the plaintext is dropped before any logging.

## Reset tokens

- 32-byte URL-safe random tokens (`secrets.token_urlsafe(32)`).
- Stored hashed (sha256) in the `sessions`-style table that lands in Phase 2.
  For Phase 1, the token is logged to the dev console only, and the API
  always returns 204 regardless of whether the email exists.
- Single use; expires 1 hour after issuance.

## CORS

Allowed origins restricted to `FRONTEND_ORIGIN`. Credentials are allowed so
the session cookie can be sent.

## What is *not* yet addressed

These land alongside the features that need them:

- Rate limiting on `/auth/*` (Phase 7).
- Audit log of sensitive operations (Phase 2+).
- Encryption at rest for sensitive columns (Phase 2+ if needed; not required
  for the financial calculator to function).
- Two-factor authentication (out of scope for Phase 1).
- Document upload (Phase 7+, requires explicit consent UI per spec §13).

## Reporting

If you find a security issue, please do not file a public issue. Contact the
maintainers directly. (Placeholder; replace with the real address before
going to production.)