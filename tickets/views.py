

# ☆ Purpose:Purpose: defines the actual logic behind each API endpoint — what happens on GET/POST/PUT/DELETE. 
# With DRF's ModelViewSet, you get all five CRUD operations for free from one class.

# Imports:
from rest_framework import viewsets
from .models import Ticket, Project, Comment
from .serializers import ProjectSerializer, TicketSerializer, CommentSerializer
from .permissions import IsOwnerOrAdmin, IsAdminOrReadOnly

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAdminOrReadOnly]

class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [IsOwnerOrAdmin]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAdminOrReadOnly]
