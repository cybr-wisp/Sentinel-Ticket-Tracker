# Sentinel Ticket Tracker

A security-hardened defect-tracking REST API built with Django and Django REST Framework.

Sentinel was developed with an adversarial testing mindset: security requirements are encoded as automated tests, and the test suite has already uncovered and prevented three real authorization and data-integrity vulnerabilities in the codebase.

**Live demo:** Coming soon
**Stack:** Python · Django · Django REST Framework · PostgreSQL · Redis · OAuth 2.0 with PKCE · Docker · GitHub Actions

---

## Overview

Sentinel is a multi-project defect and ticket tracking system.

Projects contain tickets, tickets include status, priority, ownership, and assignment information, and each ticket can contain a threaded discussion through comments.

All application access is provided through a REST API protected by OAuth 2.0 authorization-code authentication with PKCE and object-level authorization rules.

### Core capabilities

* Multi-project ticket management
* Ticket status, priority, ownership, and assignment tracking
* Ticket comment threads
* OAuth 2.0 authorization-code authentication with PKCE
* Role-based and object-level permissions
* Redis-backed rate limiting
* PostgreSQL persistence
* Automated integration, authorization, and security testing
* Dockerized local development
* Continuous integration with GitHub Actions

---

## Security Model

Security is treated as a core application requirement rather than a final deployment step.

### Private-by-default API

Every API endpoint requires authentication.

Object-level authorization rules are applied after authentication:

* Users may access tickets they own
* Staff users receive elevated administrative permissions
* Ticket deletion is restricted to staff
* Ticket ownership is derived from the authenticated requester rather than client-supplied input

Restricting ticket deletion allows tickets to function as persistent audit records.

### OAuth 2.0 with PKCE

Authentication is implemented using `django-oauth-toolkit` and the OAuth 2.0 authorization-code flow with Proof Key for Code Exchange.

The implementation includes:

* Authorization-code authentication
* PKCE verification
* Access-token validation
* Token revocation
* Explicit rejection of expired, malformed, tampered, missing, and revoked tokens

OAuth functionality is delegated to a maintained library rather than implemented from scratch.

### Transport and session hardening

The application enables and tests:

* HTTPS redirection
* Secure cookies
* HTTP-only cookies
* CSRF protection
* TLS-enabled local development using gitignored self-signed certificates

### Redis-backed rate limiting

Credential-submission endpoints are protected by a custom Redis-backed rate limiter.

The limiter allows:

* **5 POST requests**
* **Per 60-second window**
* **Per IP address**
* **Per request path**

The implementation is intentionally restricted to POST requests so ordinary login-page requests are not counted as authentication attempts.

#### Failure behavior

The limiter fails open when Redis is unavailable.

Authentication therefore remains available during a Redis outage, while the degraded rate-limiting state is recorded in application logs. Rate limiting is treated as defense in depth rather than the primary authentication control.

#### TTL safety

The limiter uses Redis increment and expiry operations with `EXPIRE ... NX` on every request.

This design:

* Prevents counters from persisting indefinitely
* Reduces the impact of an interruption between increment and expiry operations
* Restores missing expiration values automatically

---

## Testing and Verification

The project currently includes:

* **52 automated tests**
* **95% overall test coverage**
* **100% coverage across authentication-critical components**
* **An enforced CI coverage threshold of 85%**

The following areas are maintained at 100% coverage:

* Permissions
* Middleware
* Views
* Serializers
* Models
* Security-related settings

Tests run automatically in GitHub Actions on every push.

```bash
pytest --cov --cov-fail-under=85
```

### What the suite verifies

#### OAuth 2.0 and PKCE

The suite exercises the complete authorization-code and PKCE flow from authorization through token exchange.

It also verifies rejection of:

* Expired access tokens
* Tampered access tokens
* Missing tokens
* Revoked tokens
* Incorrect PKCE verifiers

#### Object-level authorization and IDOR prevention

A valid authenticated user cannot read, modify, or delete another user's tickets by directly requesting their object identifiers.

These controls are tested with both:

* Session authentication
* OAuth 2.0 bearer-token authentication

This demonstrates that authorization behavior remains consistent across authentication methods.

#### Mass-assignment prevention

Client-supplied ownership fields are ignored during ticket creation.

For example, a payload containing:

```json
{
  "created_by": "another-user"
}
```

cannot assign ownership to another account. Ownership is always derived from the authenticated requester.

#### Rate-limiter behavior

The tests verify:

* A `429 Too Many Requests` response on the sixth attempt
* Independent buckets for separate IP addresses
* Independent buckets for separate request paths
* Correct expiration behavior
* Graceful fail-open behavior during a simulated Redis outage

#### Transport and session security

The suite verifies:

* HTTPS redirection
* Secure cookie configuration
* HTTP-only cookie configuration
* CSRF enforcement

---

## Security Findings Discovered During Development

The tests were written against intended security behavior rather than the existing implementation. In three cases, the implementation failed those expectations and exposed real defects.

| Finding                                                                           | Risk                                                            | Resolution                                                               |
| --------------------------------------------------------------------------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `Comment.author` stored usernames in a `CharField`                                | No referential integrity and no reliable user-deletion behavior | Replaced with a foreign key and added a database migration               |
| Project and comment endpoints allowed anonymous reads                             | Unauthorized information disclosure                             | Applied authentication requirements and added permanent regression tests |
| An “admin or read-only” permission allowed authenticated users to create projects | Privilege escalation through unintended write access            | Restricted all project write operations to staff users                   |

These findings are now permanently covered by regression tests.

---

## Architecture Decisions

### Relationship-specific deletion behavior

Deletion behavior is selected according to the meaning of each relationship.

Ownership and authorship relationships use `SET_NULL`:

* `Ticket.created_by`
* `Comment.author`

Tickets and comments are historical records and should remain available after the originating user account is deleted.

Containment relationships use `CASCADE`:

* `Ticket.project`
* `Comment.ticket`

A ticket has no meaning without its project, and a comment has no meaning without its ticket.

### Built-in staff roles

Sentinel uses Django's built-in `is_staff` field rather than introducing a custom user model.

The application currently requires only two authorization levels:

* Standard user
* Staff administrator

Using the built-in role system avoids a migration-heavy custom user implementation that would provide little additional value for the current requirements.

### Maintained OAuth implementation

OAuth 2.0 is implemented through `django-oauth-toolkit`.

Authentication and token handling are not implemented manually because security-sensitive protocol implementations should rely on maintained, tested libraries whenever possible.

PKCE is enabled to strengthen the authorization-code exchange.

### Custom rate-limit middleware

The rate limiter was implemented directly rather than through `django-ratelimit` to explore:

* Redis-backed request counting
* Per-IP and per-path bucket design
* Fail-open versus fail-closed behavior
* Expiration handling
* Counter and TTL race conditions

The resulting design decisions are documented and covered by automated tests.

### Least-privilege test database

The application's PostgreSQL role does not have `CREATEDB` privileges.

For native development:

* The test database is created separately by a privileged PostgreSQL user
* Tests reuse the existing database with `--reuse-db`

In CI, GitHub Actions starts an isolated PostgreSQL service container, allowing tests to run in an ephemeral environment.

### Shared configuration across environments

The application uses one environment-variable-based settings system for both native and containerized development.

Local defaults use standard localhost addresses. Docker Compose overrides only the required service locations, including:

* `DB_HOST`
* `REDIS_HOST`

The same application code therefore runs natively and in Docker without environment-specific feature flags.

---

## Getting Started

### Docker setup

Docker is the recommended way to run Sentinel locally.

```bash
cp .env.example .env
```

Update the required values in `.env`, then build and start the services:

```bash
docker compose up --build
```

Apply database migrations:

```bash
docker compose exec app python manage.py migrate
```

Create an administrative account:

```bash
docker compose exec app python manage.py createsuperuser
```

The API is available at:

```text
http://localhost:8000/api/
```

An anonymous request should receive a `401 Unauthorized` response. This confirms that the private-by-default permission policy is active.

### Running tests locally

Install the project dependencies:

```bash
pip install -r requirements.txt
```

Run the test suite:

```bash
pytest
```

The native test environment requires PostgreSQL configuration through `.env.example`.

A live Redis instance is not required during testing because `fakeredis` is injected through an automatically applied fixture.

---

## Known Limitations

* Comment creation is currently restricted to staff users. Object-level comment ownership permissions are planned.
* Rate limiting currently uses `REMOTE_ADDR`.
* Deployments behind a reverse proxy will require trusted-proxy configuration and careful handling of forwarded IP headers.
* Free-tier hosting may introduce a delayed response after periods of inactivity.


