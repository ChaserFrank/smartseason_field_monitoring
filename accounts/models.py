"""Custom user model with explicit admin and field-agent roles."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extends Django's user model with the SmartSeason role field."""

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin (Coordinator)'
        FIELD_AGENT = 'FIELD_AGENT', 'Field Agent'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.FIELD_AGENT,
    )

    @property
    def is_admin_role(self):
        """Return True for users assigned the admin role."""
        return self.role == self.Role.ADMIN

    @property
    def is_field_agent(self):
        """Return True for users assigned the field-agent role."""
        return self.role == self.Role.FIELD_AGENT

    @property
    def display_role(self):
        """Return the human-readable role label for templates and admin UI."""
        return dict(self.Role.choices).get(self.role, self.role)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.display_role})"
