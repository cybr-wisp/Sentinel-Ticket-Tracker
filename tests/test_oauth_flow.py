
import base64
import hashlib
import secrets
from urllib.parse import parse_qs, urlparse

import pytest
from rest_framework import status
from tests.conftest import CLEARTEXT_SECRET   

PROTECTED_URL = "/api/tickets/"   # CHECK: any OAuth-protected endpoint
AUTHORIZE_URL = "/o/authorize/"
TOKEN_URL = "/o/token/"


def make_pkce_pair():
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


@pytest.mark.django_db
class TestFullAuthorizationCodeFlow:

    def test_full_flow_with_pkce(self, api_client, regular_user, oauth_application):
        """The centerpiece: authorize -> code -> token exchange -> use token."""
        verifier, challenge = make_pkce_pair()
        api_client.force_login(regular_user)  # authorize step needs a session

        # Step 1: authorization request
        resp = api_client.get(AUTHORIZE_URL, {
            "response_type": "code",
            "client_id": oauth_application.client_id,
            "redirect_uri": oauth_application.redirect_uris,
            "scope": "read write",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        })
        assert resp.status_code == 200  # consent form rendered

        # Step 2: user consents (POST the form)
        resp = api_client.post(AUTHORIZE_URL, {
            "client_id": oauth_application.client_id,
            "redirect_uri": oauth_application.redirect_uris,
            "response_type": "code",
            "scope": "read write",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "allow": "Authorize",
        })
        assert resp.status_code == 302
        code = parse_qs(urlparse(resp["Location"]).query)["code"][0]

        # Step 3: exchange code + verifier for tokens
        resp = api_client.post(TOKEN_URL, {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": oauth_application.redirect_uris,
            "client_id": oauth_application.client_id,
            "client_secret": CLEARTEXT_SECRET,  # CHECK: see note below
            "code_verifier": verifier,
        })
        assert resp.status_code == 200
        tokens = resp.json()
        assert "access_token" in tokens and "refresh_token" in tokens

        # Step 4: the token actually works
        api_client.logout()  # prove it's the TOKEN granting access, not the session
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")
        resp = api_client.get(PROTECTED_URL)
        assert resp.status_code == status.HTTP_200_OK

    def test_wrong_pkce_verifier_rejected(
        self, api_client, regular_user, oauth_application
    ):
        _, challenge = make_pkce_pair()
        api_client.force_login(regular_user)
        resp = api_client.post(AUTHORIZE_URL, {
            "client_id": oauth_application.client_id,
            "redirect_uri": oauth_application.redirect_uris,
            "response_type": "code",
            "scope": "read write",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "allow": "Authorize",
        })
        code = parse_qs(urlparse(resp["Location"]).query)["code"][0]

        wrong_verifier, _ = make_pkce_pair()  # fresh pair = mismatched verifier
        resp = api_client.post(TOKEN_URL, {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": oauth_application.redirect_uris,
            "client_id": oauth_application.client_id,
            "client_secret": CLEARTEXT_SECRET,
            "code_verifier": wrong_verifier,
        })
        assert resp.status_code == 400
        assert "access_token" not in resp.json()


@pytest.mark.django_db
class TestTokenRejection:

    def test_valid_token_accepted(self, api_client, regular_user, token_for):
        t = token_for(regular_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {t.token}")
        assert api_client.get(PROTECTED_URL).status_code == status.HTTP_200_OK

    def test_expired_token_rejected(self, api_client, regular_user, token_for):
        t = token_for(regular_user, expired=True)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {t.token}")
        assert api_client.get(PROTECTED_URL).status_code == status.HTTP_401_UNAUTHORIZED

    def test_tampered_token_rejected(self, api_client, regular_user, token_for):
        t = token_for(regular_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {t.token[:-4]}XXXX")
        assert api_client.get(PROTECTED_URL).status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_token_rejected(self, api_client):
        resp = api_client.get(PROTECTED_URL)
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN
        )

    def test_revoked_token_rejected(self, api_client, regular_user, token_for):
        """Replay: a token that WAS valid must stop working after revocation."""
        t = token_for(regular_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {t.token}")
        assert api_client.get(PROTECTED_URL).status_code == status.HTTP_200_OK  # was valid
        t.delete()  # upgrade later: POST /o/revoke_token/ (RFC 7009)
        assert api_client.get(PROTECTED_URL).status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestAuthMethodInvariance:

    def test_ownership_enforced_over_bearer_auth(
        self, api_client, other_user, ticket, token_for
    ):
        """The continuity invariant: IsOwnerOrAdmin must hold regardless of HOW
        identity arrived — session or Bearer token."""
        t = token_for(other_user)  # attacker's perfectly VALID token
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {t.token}")
        resp = api_client.patch(f"{PROTECTED_URL}{ticket.id}/", {"title": "hacked"})
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        ticket.refresh_from_db()
        assert ticket.title != "hacked"