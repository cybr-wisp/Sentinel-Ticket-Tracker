

# ☆ Purpose: converts your Django model objects ↔ JSON. When the API receives a POST request with JSON, 
# the serializer validates it and turns it into a Ticket object. When you fetch a Ticket to send back 
# as a response, the serializer turns it into JSON.

# Imports 
from .models import Ticket, Project, Comment
from rest_framework import serializers


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = "__all__"

class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = "__all__"
        read_only_fields = ['created_by']

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = '__all__'



