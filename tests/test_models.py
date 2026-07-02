
import pytest
from django.core.exceptions import ValidationError
from tickets.models import Project, Ticket, Comment  # CHECK: does Comment exist?


@pytest.mark.django_db
class TestTicketModel:

    def test_deleting_user_preserves_ticket(self, ticket, regular_user):
        """created_by is SET_NULL: tickets are historical records that outlive their reporter."""
        ticket_id = ticket.id
        regular_user.delete()
        ticket.refresh_from_db()
        assert ticket.created_by is None
        assert Ticket.objects.filter(id=ticket_id).exists()

    def test_deleting_project_cascades_tickets(self, project, ticket):
        """project FK is CASCADE: a ticket is meaningless outside its project."""
        ticket_id = ticket.id
        project.delete()
        assert not Ticket.objects.filter(id=ticket_id).exists()

    def test_ticket_defaults(self, project, regular_user):
        t = Ticket.objects.create(
            project=project, title="Minimal ticket", created_by=regular_user
        )
        assert t.status == "open"        # CHECK: your declared defaults
        assert t.priority == "medium"    # CHECK

    def test_invalid_status_rejected_by_validation(self, ticket):
        """Django validates choices in full_clean(), NOT in save()."""
        ticket.status = "banana"
        with pytest.raises(ValidationError):
            ticket.full_clean()

    def test_invalid_priority_rejected_by_validation(self, ticket):
        ticket.priority = "ultra-mega-high"
        with pytest.raises(ValidationError):
            ticket.full_clean()

    def test_str_representation(self, ticket):
        assert str(ticket) == "[MEDIUM] Login page throws 500"  # CHECK: your __str__


@pytest.mark.django_db
class TestCommentModel:  # CHECK: delete this class if Comment doesn't exist

    @pytest.fixture
    def comment(self, ticket, regular_user):
        return Comment.objects.create(
            ticket=ticket, author=regular_user, body="Reproduced on staging"
        )

    def test_deleting_ticket_cascades_comments(self, ticket, comment):
        comment_id = comment.id
        ticket.delete()
        assert not Comment.objects.filter(id=comment_id).exists()

    def test_deleting_user_nullifies_comment_author(self, comment, regular_user):
        comment_id = comment.id
        regular_user.delete()
        comment.refresh_from_db()
        assert comment.author is None
        assert Comment.objects.filter(id=comment_id).exists()
    
    def test_comment_str_representation(self, comment, regular_user, ticket):
        assert str(comment) == f"Comment by {regular_user} on {ticket}"

@pytest.mark.django_db # These tests need permission to use the test database 
class TestProjectModel:
    
    # comes from the pytest fixture - inside confest.py 
    def test_project_creation(self, project):
        assert project.name == "Fifth Sense"
        # did we automatically fill in the creation date 
        assert project.created_at is not None  # CHECK: does Project have this field?

    def test_project_str_representation(self, project):
        assert str(project) == "Fifth Sense"  # CHECK: assumes __str__ returns self.name
    
    