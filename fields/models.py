"""Domain models for field lifecycle tracking and audit history."""

from django.db import models
from django.utils import timezone
from django.conf import settings


class Field(models.Model):
    """Represents a monitored crop field and its current lifecycle state."""

    class Stage(models.TextChoices):
        PLANTED = 'PLANTED', 'Planted'
        GROWING = 'GROWING', 'Growing'
        READY = 'READY', 'Ready'
        HARVESTED = 'HARVESTED', 'Harvested'

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        AT_RISK = 'AT_RISK', 'At Risk'
        COMPLETED = 'COMPLETED', 'Completed'

    name = models.CharField(max_length=200)
    crop_type = models.CharField(max_length=100)
    planting_date = models.DateField()
    current_stage = models.CharField(
        max_length=20,
        choices=Stage.choices,
        default=Stage.PLANTED,
    )
    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_fields',
        limit_choices_to={'role': 'FIELD_AGENT'},
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            # PostgreSQL indexes support the dashboard's most common filters.
            models.Index(fields=['assigned_agent'], name='idx_field_agent'),
            # Stage filtering is used by list and dashboard views.
            models.Index(fields=['current_stage'], name='idx_field_stage'),
            # Planting age is checked on every status evaluation.
            models.Index(fields=['planting_date'], name='idx_field_planting_date'),
            # Compound index supports agent-scoped stage filters.
            models.Index(fields=['assigned_agent', 'current_stage'], name='idx_field_agent_stage'),
        ]

    def __str__(self):
        return f"{self.name} ({self.crop_type})"

    @property
    def computed_status(self):
        """
        Derives the current status from stage, planting age, and recent updates.

        The value is intentionally computed on access rather than persisted to
        avoid stale derived state after new updates are created.
        """
        if self.current_stage == self.Stage.HARVESTED:
            return self.Status.COMPLETED

        today = timezone.now().date()
        days_since_planting = (today - self.planting_date).days

        # Age plus stage determines whether a field is trending behind schedule.
        early_stages = [self.Stage.PLANTED, self.Stage.GROWING]
        if days_since_planting > 90 and self.current_stage in early_stages:
            return self.Status.AT_RISK

        # Recent updates are part of the risk calculation for active fields.
        last_update = self.updates.order_by('-created_at').first()
        if last_update:
            days_since_update = (timezone.now() - last_update.created_at).days
            if days_since_update > 14:
                return self.Status.AT_RISK
        else:
            # No updates ever — if planted more than 14 days ago, at risk
            if days_since_planting > 14:
                return self.Status.AT_RISK

        return self.Status.ACTIVE

    @property
    def status_badge_class(self):
        status = self.computed_status
        return {
            self.Status.ACTIVE: 'badge-active',
            self.Status.AT_RISK: 'badge-at-risk',
            self.Status.COMPLETED: 'badge-completed',
        }.get(status, 'badge-active')

    @property
    def stage_progress(self):
        """Returns the coarse progress percentage implied by the current stage."""
        return {
            self.Stage.PLANTED: 25,
            self.Stage.GROWING: 50,
            self.Stage.READY: 75,
            self.Stage.HARVESTED: 100,
        }.get(self.current_stage, 0)

    @property
    def days_since_planted(self):
        return (timezone.now().date() - self.planting_date).days


class FieldUpdate(models.Model):
    """Stores an auditable stage transition for a field.

    Both previous_stage and new_stage are persisted so reports can reconstruct
    the exact transition history later.
    """

    field = models.ForeignKey(
        Field,
        on_delete=models.CASCADE,
        related_name='updates',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='field_updates',
    )
    previous_stage = models.CharField(max_length=20, choices=Field.Stage.choices)
    new_stage = models.CharField(max_length=20, choices=Field.Stage.choices)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            # Timeline queries need field-scoped ordering by date.
            models.Index(fields=['field', '-created_at'], name='idx_update_field_date'),
            # Recent-activity feeds scan newest updates across all fields.
            models.Index(fields=['-created_at'], name='idx_update_created_at'),
        ]

    def __str__(self):
        return f"{self.field.name}: {self.previous_stage} → {self.new_stage}"
