
# OWASP ZAP Security Scan Report

**Target:** `https://sentinel-anis.onrender.com`
**Scanner:** OWASP ZAP (baseline scan, Dockerized `zaproxy/zaproxy:stable`)
**Scan type:** Passive + light-active, unauthenticated (anonymous attacker surface)

## Summary

| Result | Before fix | After fix |
|---|---|---|
| **High / Critical (FAIL)** | **0** | **0** |
| Warnings (WARN) | 4 | 3 |
| Passed checks (PASS) | 63 | 64 |

The application passed **all** ZAP checks for the common high-severity vulnerability classes on the first scan: no SQL injection surface, no XSS, no information disclosure, no insecure cookies, no debug-error leakage, no clickjacking exposure, no CSRF-token absence. Zero High or Critical findings — before or after remediation.

## What passed (selected)

These are not defaults — each reflects a deliberate hardening decision in the application:

- **`Cookie No HttpOnly Flag` / `Cookie Without Secure Flag`** — session and CSRF cookies carry `Secure` and `HttpOnly`.
- **`Information Disclosure - Debug Error Messages`** — confirms `DEBUG=False` is active in production (no stack traces leak to clients).
- **`Absence of Anti-CSRF Tokens`** — CSRF protection present.
- **`Cross-Domain Misconfiguration`** — no permissive CORS.
- **`Heartbleed OpenSSL Vulnerability`** — TLS stack not vulnerable.
- **`Weak Authentication Method`** — authentication scheme sound (OAuth2 + PKCE).

## Findings and remediation

### Fixed: Strict-Transport-Security (HSTS) header not set

**Finding (initial scan):** `Strict-Transport-Security Header Not Set [10035]` — WARN.

Without HSTS, a browser that first reaches the site over HTTP could be downgrade-attacked before the redirect to HTTPS. HSTS instructs browsers to use HTTPS exclusively for a defined period.

**Fix:** enabled via Django's `SecurityMiddleware` in `settings.py`:

```python
SECURE_HSTS_SECONDS = 31536000          # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
```

**Result (rescan):** `Strict-Transport-Security Header [10035]` — **PASS**. Warning count dropped from 4 to 3; passed checks rose from 63 to 64.

This before/after pair is preserved in `zap-scan-before.html` and `zap-scan-after.html`.

## Deferred findings (documented, not fixed)

The remaining three warnings are retained deliberately, with rationale — this is a JSON REST API, not a browser-rendered web application, which changes the value of certain headers.

### Content-Security-Policy (CSP) not set — deferred

CSP governs which sources a **browser** may load and execute scripts, styles, and other resources from within a rendered HTML page. This API serves JSON responses that browsers do not execute as pages, so CSP provides little practical protection here. It would become relevant if a browser-based frontend is added; it is planned for that milestone.

### Permissions-Policy not set — deferred

Permissions-Policy controls browser feature access (camera, geolocation, etc.) for rendered pages. As with CSP, this applies to browser-executed HTML, not a JSON API surface. Deferred for the same reason.

### Storable and Cacheable Content — accepted (low severity)

ZAP flags that some responses (notably 404s at paths the API does not serve) are cacheable. Severity is low and there is no sensitive data in these responses. No action taken.

## How to reproduce

```bash
docker run --rm -t -v ${PWD}:/zap/wrk ghcr.io/zaproxy/zaproxy:stable \
  zap-baseline.py -t https://sentinel-anis.onrender.com -r zap-report.html
```

For a deeper crawl of the API endpoints, target the API root directly:
`-t https://sentinel-anis.onrender.com/api/`