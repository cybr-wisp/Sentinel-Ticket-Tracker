
# Imports
import uuid
from datetime import timedelta

import fakeredis
import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from oauth2_provider.models import Application, AccessToken
from rest_framework.test import APIClient

from tickets.models import Project, Ticket

CLEARTEXT_SECRET = "test-client-secret"   # near the top, after imports

# ---- clients ----
@pytest.fixture
def api_client():
    return APIClient()


# ---------- users: victim, attacker, admin ----------

@pytest.fixture
def regular_user(db):
    return User.objects.create_user(username="marie", password="testpass123")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="mallory", password="testpass123")


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="admin", password="testpass123", is_staff=True
    )


# ---------- domain objects ----------
@pytest.fixture
def project(db):
    return Project.objects.create(name="Fifth Sense", description="Test project")


@pytest.fixture
def ticket(project, regular_user):
    # CHECK: match your Ticket model's required fields exactly
    return Ticket.objects.create(
        project=project,
        title="Login page throws 500",
        created_by=regular_user,
    )

# ---------- oauth ----------

@pytest.fixture
def oauth_application(regular_user):
    return Application.objects.create(
        name="Test Client",
        user=regular_user,
        client_secret=CLEARTEXT_SECRET,
        client_type=Application.CLIENT_CONFIDENTIAL,
        authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        # CHECK: use the redirect URI you registered in Days 8-11
        redirect_uris="https://localhost:8000/callback/",
    )


@pytest.fixture
def token_for(oauth_application):
    def make_token(user, expired=False):
        delta = timedelta(hours=-1) if expired else timedelta(hours=1)
        return AccessToken.objects.create(
            user=user,
            application=oauth_application,
            token=f"test-{user.username}-{uuid.uuid4().hex}",
            expires=timezone.now() + delta,
            scope="read write",
        )
    return make_token


# ---------- environment control (autouse — applies to every test) ----------

@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    fake = fakeredis.FakeRedis()
    monkeypatch.setattr("tickets.middleware.redis_client", fake)
    return fake


@pytest.fixture(autouse=True)
def no_ssl_redirect(settings):
    settings.SECURE_SSL_REDIRECT = False
