
# ☆ Purpose: models.py defines the core data structures for Sentinel Ticket Tracker's domain layer.
# It declares the Project, Ticket, and Comment entities, their fields, and the relationships between them (e.g. a Ticket belongs to a Project, a Comment belongs to a Ticket). 
# These Python classes are translated by Django's ORM into actual PostgreSQL tables via migrations, and serve as the foundation that the admin interface, 
# REST API serializers, and views are all built on top of.

# Imports
from django.db import models
from django.contrib.auth.models import User
# Brings in Django's field types (CharField, TextField, etc.)
# and the base "Model" class every database table inherits from.

class Project(models.Model):
    # Inheriting from models.Model = this class becomes a DB table.
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Ticket(models.Model): 
    # List of Status Choices - drop down menu
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
    ]
        
    # List of Priority Choices - drop down menu 
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tickets')
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets_created')

    def __str__(self):
        return f"[{self.priority.upper()}] {self.title}"

class Comment(models.Model):

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    author = models.CharField(max_length=150)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author} on {self.ticket}"

