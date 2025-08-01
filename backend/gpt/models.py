from django.db import models
from django.contrib.auth import get_user_model

class Role(models.Model):
    name = models.CharField(max_length=255)  # e.g., Admin, User

    def __str__(self):
        return self.name

class Permission(models.Model):
    name = models.CharField(max_length=255)  # e.g., can_edit, can_delete
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='permissions')

    def __str__(self):
        return f"{self.name} - {self.role}"

User = get_user_model()

class SomeModel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
