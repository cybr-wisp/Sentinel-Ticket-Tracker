
![CI](https://github.com/cybr-wisp/Sentinel-Ticket-Tracker/actions/workflows/ci.yml/badge.svg)

# Sentinel Ticket Tracker

![CI](https://github.com/cybr-wisp/Sentinel-Ticket-Tracker/actions/workflows/ci.yml/badge.svg)

A security-hardened defect-tracking REST API built with Django and Django REST Framework, developed with an adversarial testing mindset: every architectural decision is enforced by a test, and the test suite has already caught and fixed three real security findings in this codebase.

<!-- CHECK: add live URL once Render deploy is done -->
**Live demo:** _coming soon_ · **Stack:** Django · DRF · PostgreSQL · Redis · OAuth2 (PKCE) · Docker · GitHub Actions

---

## What it does

Sentinel is a multi-project defect tracker: projects contain tickets, tickets carry status/priority and ownership, and tickets have comment threads. All access is through a REST API protected by OAuth2 (authorization code + PKCE) with object-level ownership permissions.

## Security posture

This project treats security as the feature, not an afterthought:

- **Private-by-default API.** Every endpoint requires authentication. Object-level rules layer on top: users own their tickets; admins (staff) hold elevated rights; ticket deletion is reserved for staff so tickets function as audit records.
- **OAuth2 with PKCE**, via `django-oauth-toolkit`, including token revocation. Client secrets are hashed at rest by the library.
- **TLS in development** (self-signed certs, gitignored), `SECURE_SSL_REDIRECT`, and all secure cookie flags (`Secure`, `HttpOnly`) enabled and tested.
- **CSRF protection verified two independent ways** in tests.
- **Hand-written Redis rate limiter** on credential-submission endpoints (login, token exchange): 5 POSTs per 60s per IP per path. Designed deliberately:
  - *Fails open* — if Redis is unreachable, authentication stays available (rate limiting is defense-in-depth, not the primary control), and the degradation is logged.
  - TTL set with `EXPIRE ... NX` on every request, closing the classic INCR/EXPIRE crash race and self-healing lost TTLs.
  - Scoped to POST only — loading a login page is not an attack.

## Test suite: 52 tests, 95% coverage, 100% on the auth-critical path

Coverage is enforced in CI on every push (`--cov-fail-under=85`). The security-critical files — permissions, middleware, views, serializers, models, settings — sit at **100%**.

Highlights of what the suite actually proves:

- **Full OAuth2 authorization-code + PKCE flow end to end**, plus explicit rejection tests: expired, tampered, missing, and revoked tokens, and a wrong PKCE verifier at token exchange.
- **IDOR coverage**: a valid user cannot read-modify-delete another user's tickets by ID — proven over both session auth *and* Bearer tokens (the permission layer is authentication-method invariant).
- **Mass-assignment defense**: a create payload claiming `created_by: <someone else>` is ignored; ownership always derives from the authenticated requester.
- **Rate limiter behavior**: 429 on the 6th attempt, independent per-IP and per-path buckets, TTL invariant, and graceful fail-open under a simulated Redis outage.
- **Transport & session hardening**: HTTPS redirect, cookie flags, CSRF enforcement.

### Three real findings caught by this suite

The tests were written against *intent*, and three times reality disagreed:

1. **Schema bug** — `Comment.author` was a `CharField` storing a copy of the username: no referential integrity, no `SET_NULL` semantics. Converted to a proper FK with a migration.
2. **Information disclosure** — after locking down tickets, coverage analysis of the permission layer revealed the project and comment endpoints still allowed anonymous reads. Closed and permanently pinned by tests.
3. **Privilege escalation** — a permission class named "admin or read-only" allowed *any* authenticated user to create projects (the staff check only guarded edits). Fixed so all writes require staff.

## Architecture decisions

- **`on_delete` as a per-relationship judgment**: ownership/authorship links (`Ticket.created_by`, `Comment.author`) use `SET_NULL` — records are history and outlive their author. Containment links (`Ticket.project`, `Comment.ticket`) use `CASCADE` — a child is meaningless without its parent.
- **Built-in `is_staff` as the role flag** rather than a custom user model — avoids a migration-breaking retroactive change for a two-role system.
- **`django-oauth-toolkit` over hand-rolled auth** — implementing OAuth2 from scratch is an anti-pattern; PKCE is enabled even though optional for confidential clients.
- **Hand-written rate-limit middleware over `django-ratelimit`** — chosen for learning value; the fail-open/fail-closed decision and the INCR/EXPIRE race are documented above.
- **Least-privilege test database**: the app's Postgres role cannot `CREATEDB`; the test database is pre-created by a superuser and reused (`--reuse-db`). In CI, an ephemeral Postgres container makes this moot — strict where it matters, pragmatic where it doesn't.
- **One `.env`, two environments**: settings read `os.environ` with localhost defaults; Docker Compose surgically overrides `DB_HOST`/`REDIS_HOST` to service names. Same codebase runs natively and containerized with no flags.

<!-- CHECK: consider adding your architecture diagram here: ![Architecture](docs/architecture.png) -->

## Running it

**With Docker (recommended):**

```bash
cp .env.example .env        # fill in values
docker compose up --build
docker compose exec app python manage.py migrate
docker compose exec app python manage.py createsuperuser
```

API at `http://localhost:8000/api/` (401 for anonymous requests is the permission layer working).

**Tests (native):**

```bash
pip install -r requirements.txt
pytest          # 52 tests; coverage gate at 85% enforced
```

Requires local PostgreSQL; see `.env.example` for configuration. Redis is not required for tests (`fakeredis` is injected via an autouse fixture).

## Known limitations

- Comment creation is currently staff-only (comment ownership permissions are a planned fast-follow).
- `REMOTE_ADDR`-based rate limiting assumes no reverse proxy; behind one, `X-Forwarded-For` handling (trusting only the proxy) is required.
- Free-tier hosting spins down after inactivity — first request after idle may be slow. <!-- CHECK: keep or remove depending on final hosting -->

## Roadmap

- OWASP ZAP baseline scan with documented findings and remediation (`docs/zap-scan-report.md`)
- Load testing with locust (p95 latency under 50 concurrent users, reported locally and deployed)
- Comment ownership permissions

---

<!-- CHECK: add your name / links -->
Built by Marie <!-- CHECK --> as a security-focused backend portfolio project.