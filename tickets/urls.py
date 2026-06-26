
# ☆ Purpose: maps URL paths to your viewsets — this is what actually turns TicketViewSet into a real, 
# reachable endpoint like /tickets/. Without this file, your viewsets exist in Python but nothing on the web can reach them.

from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet, TicketViewSet, CommentViewSet

router = DefaultRouter() # Create a Router Instance 
router.register(r'projects', ProjectViewSet)
router.register(r'tickets', TicketViewSet)
router.register(r'comments', CommentViewSet)

urlpatterns = router.urls