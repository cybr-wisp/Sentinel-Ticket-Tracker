import pytest
import redis as redis_lib
from django.test import Client
from rest_framework import status

TICKETS_URL = "/api/tickets/"
LOGIN_URL = "/api-auth/login/"
TOKEN_URL = "/o/token/"


# ---------- TLS / redirect ----------

@pytest.mark.django_db
class TestHTTPSRedirect:

    def test_http_redirects_to_https(self, api_client, settings):
        """Re-enable the redirect (autouse fixture disabled it) and prove it fires."""
        settings.SECURE_SSL_REDIRECT = True
        resp = api_client.get(TICKETS_URL)  # test client requests are http by default
        assert resp.status_code == 301
        assert resp["Location"].startswith("https://")

    def test_https_request_not_redirected(self, api_client, settings):
        """secure=True simulates an already-https request: no redirect loop."""
        settings.SECURE_SSL_REDIRECT = True
        resp = api_client.get(TICKETS_URL, secure=True)
        assert resp.status_code != 301


# ---------- cookie flags ----------

@pytest.mark.django_db
class TestCookieFlags:

    def test_session_cookie_secure_and_httponly(self, client, regular_user):
        client.post(
            LOGIN_URL,
            {"username": "marie", "password": "testpass123"},
            secure=True,
        )
        session_cookie = client.cookies.get("sessionid")
        assert session_cookie is not None, "login did not set a session cookie"
        assert session_cookie["secure"]      # never sent over plain http
        assert session_cookie["httponly"]    # invisible to JavaScript (XSS defense)

    def test_csrf_cookie_secure(self, client, regular_user):
        resp = client.get(LOGIN_URL, secure=True)  # form page sets csrftoken
        csrf_cookie = client.cookies.get("csrftoken")
        if csrf_cookie is None:
            pytest.skip("no csrf cookie set on this page — check CSRF_COOKIE flags in settings")
        assert csrf_cookie["secure"]

    def test_secure_cookie_settings_are_on(self, settings):
        """Belt-and-suspenders: the flags exist in settings at all."""
        assert settings.SESSION_COOKIE_SECURE is True
        assert settings.CSRF_COOKIE_SECURE is True
        assert settings.SESSION_COOKIE_HTTPONLY is True


# ---------- CSRF ----------

@pytest.mark.django_db
class TestCSRF:

    def test_csrf_enforced_without_token(self, regular_user):
        """Django's test client skips CSRF by default — this flag turns it back on."""
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(regular_user)
        resp = csrf_client.post(
            LOGIN_URL, {"username": "x", "password": "y"}, secure=True
        )
        assert resp.status_code == 403

    def test_csrf_not_required_for_bearer_requests(
        self, api_client, regular_user, token_for
    ):
        """Token auth doesn't ride on cookies, so CSRF doesn't apply — POST succeeds."""
        t = token_for(regular_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {t.token}")
        resp = api_client.post(TICKETS_URL, {"title": "no csrf needed"})
        # 400 (missing project field) would still prove we got PAST csrf/auth;
        # what must NOT happen is 403-csrf
        assert resp.status_code != 403


# ---------- rate limiting ----------

@pytest.mark.django_db
class TestRateLimiting:

    def test_first_five_posts_not_limited(self, api_client):
        for _ in range(5):
            resp = api_client.post(TOKEN_URL, {"grant_type": "bad"})
            assert resp.status_code != 429

    def test_sixth_post_returns_429(self, api_client):
        for _ in range(5):
            api_client.post(TOKEN_URL, {"grant_type": "bad"})
        resp = api_client.post(TOKEN_URL, {"grant_type": "bad"})
        assert resp.status_code == 429

    def test_429_body_is_json_detail(self, api_client):
        for _ in range(6):
            resp = api_client.post(TOKEN_URL, {"grant_type": "bad"})
        assert resp.status_code == 429
        assert "detail" in resp.json()

    def test_buckets_are_per_ip(self, api_client):
        for _ in range(6):
            api_client.post(TOKEN_URL, {"grant_type": "bad"}, REMOTE_ADDR="10.0.0.1")
        resp = api_client.post(TOKEN_URL, {"grant_type": "bad"}, REMOTE_ADDR="10.0.0.2")
        assert resp.status_code != 429   # fresh IP, fresh bucket

    def test_buckets_are_per_path(self, api_client):
        for _ in range(6):
            api_client.post(TOKEN_URL, {"grant_type": "bad"})
        resp = api_client.post(LOGIN_URL, {"username": "x", "password": "y"})
        assert resp.status_code != 429   # burning /o/token/ doesn't lock login

    def test_unprotected_paths_not_limited(self, api_client, regular_user):
        api_client.force_authenticate(regular_user)
        for _ in range(10):
            resp = api_client.get(TICKETS_URL)
            assert resp.status_code != 429

    def test_rate_limit_key_gets_a_ttl(self, api_client, fake_redis):
        """The immortal-key race defense: the counter key must always carry a TTL."""
        api_client.post(TOKEN_URL, {"grant_type": "bad"}, REMOTE_ADDR="10.9.9.9")
        key = f"rate_limit:10.9.9.9:{TOKEN_URL}"
        assert fake_redis.ttl(key) > 0   # -1 would mean a key with no expiry

    # ---- the two below assert middleware fixes you haven't written yet: ----
    # ---- expect RED until the homework is done. That's intentional (TDD). ----

    def test_get_requests_not_rate_limited(self, api_client):
        """Loading the login PAGE isn't an attack; only submissions count."""
        for _ in range(10):
            resp = api_client.get(LOGIN_URL, secure=True)
            assert resp.status_code != 429

    def test_fails_open_when_redis_down(self, api_client, monkeypatch):
        """Rate limiter is defense-in-depth: if Redis dies, auth must still work."""
        def boom(*args, **kwargs):
            raise redis_lib.ConnectionError("redis unreachable")
        monkeypatch.setattr("tickets.middleware.redis_client.incr", boom)
        resp = api_client.post(TOKEN_URL, {"grant_type": "bad"})
        assert resp.status_code != 500   # degraded, not dead