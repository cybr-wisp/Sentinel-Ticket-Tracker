
# Imports: 
import pytest
from rest_framework import status
from tickets.models import Ticket

# Base URL 
TICKETS_URL = "/api/tickets/"  # CHECK: your router prefix from urls.py

# Targetting for a specific ticket 
def detail_url(ticket_id):
    return f"{TICKETS_URL}{ticket_id}/"

@pytest.mark.django_db 
class TestAnonymousAccess:
    def test_anonymous_cannot_list(self, api_client):
        # CHECK: if your policy is read-open, flip this to expect 200
        resp = api_client.get(TICKETS_URL)
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN
        )

    def test_anonymous_cannot_create(self, api_client, project):
        resp = api_client.post(
            TICKETS_URL, {"project": project.id, "title": "Drive-by ticket"}
        )
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN
        )


@pytest.mark.django_db
class TestOwnership:
    def test_authenticated_user_can_create(self, api_client, regular_user, project):
        api_client.force_authenticate(regular_user)

        resp = api_client.post(
            TICKETS_URL, {"project": project.id, "title": "Real bug"}
        )

        assert resp.status_code == status.HTTP_201_CREATED
        created = Ticket.objects.get(id=resp.data["id"])
        assert created.created_by == regular_user  # perform_create sets owner

    def test_created_by_cannot_be_spoofed(
        self, api_client, other_user, admin_user, project
    ):
        """Mass-assignment: a payload claiming someone else's identity is ignored."""
        api_client.force_authenticate(other_user)
        resp = api_client.post(
            TICKETS_URL,
            {
                "project": project.id,
                "title": "Spoof attempt",
                "created_by": admin_user.id,  # the lie
            },
        )
        assert resp.status_code == status.HTTP_201_CREATED
        created = Ticket.objects.get(id=resp.data["id"])
        assert created.created_by == other_user      # the truth

    def test_owner_can_update_own_ticket(self, api_client, regular_user, ticket):
        api_client.force_authenticate(regular_user)
        resp = api_client.patch(detail_url(ticket.id), {"title": "Updated title"})
        assert resp.status_code == status.HTTP_200_OK

    def test_other_user_cannot_update(self, api_client, other_user, ticket):
        """IDOR: knowing the ID of someone else's object must not grant access."""
        api_client.force_authenticate(other_user)
        resp = api_client.patch(detail_url(ticket.id), {"title": "hacked"})
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        ticket.refresh_from_db()
        assert ticket.title != "hacked"

    def test_other_user_cannot_delete(self, api_client, other_user, ticket):
        api_client.force_authenticate(other_user)
        resp = api_client.delete(detail_url(ticket.id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert Ticket.objects.filter(id=ticket.id).exists()

    def test_admin_can_update_any_ticket(self, api_client, admin_user, ticket):
        api_client.force_authenticate(admin_user)
        resp = api_client.patch(detail_url(ticket.id), {"title": "Admin edit"})
        assert resp.status_code == status.HTTP_200_OK

    def test_admin_can_delete_any_ticket(self, api_client, admin_user, ticket):
        api_client.force_authenticate(admin_user)
        resp = api_client.delete(detail_url(ticket.id))
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Ticket.objects.filter(id=ticket.id).exists()
    
    def test_authenticated_user_can_read_others_ticket(self, api_client, other_user, ticket):
        """Object-level reads are open to any authenticated user: teammates can view each other's tickets."""
        api_client.force_authenticate(other_user)
        resp = api_client.get(detail_url(ticket.id))
        assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestSerializerBoundary:
    def test_api_rejects_invalid_status(self, api_client, regular_user, project):
        """DRF serializers enforce choices at the API boundary (400), even though
        model.save() alone would not."""
        api_client.force_authenticate(regular_user)
        resp = api_client.post(
            TICKETS_URL,
            {"project": project.id, "title": "Bad status", "status": "banana"},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


PROJECTS_URL = "/api/projects/"   # CHECK against tickets/urls.py router registrations
COMMENTS_URL = "/api/comments/"   # CHECK


@pytest.mark.django_db
class TestProjectAndCommentAccess:

    def test_anonymous_cannot_list_projects(self, api_client, project):
        resp = api_client.get(PROJECTS_URL)
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN
        )

    def test_anonymous_cannot_list_comments(self, api_client):
        resp = api_client.get(COMMENTS_URL)
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN
        )

    def test_regular_user_can_read_projects(self, api_client, regular_user, project):
        api_client.force_authenticate(regular_user)
        resp = api_client.get(PROJECTS_URL)
        assert resp.status_code == status.HTTP_200_OK

    def test_regular_user_cannot_create_project(self, api_client, regular_user):
        api_client.force_authenticate(regular_user)
        resp = api_client.post(
            PROJECTS_URL, {"name": "Rogue project", "description": "should fail"}
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_create_project(self, api_client, admin_user):
        api_client.force_authenticate(admin_user)
        resp = api_client.post(
            PROJECTS_URL, {"name": "Sanctioned project", "description": "by staff"}
        )
        assert resp.status_code == status.HTTP_201_CREATED