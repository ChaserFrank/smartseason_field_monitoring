"""Shared field business rules used by both Django views and DRF endpoints."""
from django.db.models import Q
from .models import Field, FieldUpdate


def get_fields_with_status(queryset=None):
    """Return fields with related data preloaded for status-aware rendering."""
    if queryset is None:
        # Related objects are loaded up front to keep list and detail views efficient.
        queryset = Field.objects.select_related('assigned_agent').prefetch_related('updates')
    return queryset


def filter_fields(queryset, query='', stage='', status=''):
    """Apply text, stage, and derived-status filters to a field queryset."""
    if query:
        queryset = queryset.filter(
            Q(name__icontains=query) | Q(crop_type__icontains=query)
        )
    if stage:
        queryset = queryset.filter(current_stage=stage)
    # Status filtering stays in Python because it is computed, not stored.
    if status:
        return [f for f in queryset if f.computed_status == status]
    return queryset


def create_field_update(field, user, new_stage, notes=''):
    """Persist a stage transition and keep the field's current stage in sync."""
    # The service is the single source of truth for update creation.
    previous_stage = field.current_stage
    update = FieldUpdate.objects.create(
        field=field,
        updated_by=user,
        previous_stage=previous_stage,
        new_stage=new_stage,
        notes=notes,
    )
    field.current_stage = new_stage
    field.save(update_fields=['current_stage', 'updated_at'])
    return update


def get_admin_summary():
    """Compute dashboard metrics for admin visibility across all fields."""
    # Summary views need the full dataset, so related objects are prefetched once.
    all_fields = list(
        Field.objects.select_related('assigned_agent').prefetch_related('updates').all()
    )
    statuses = [f.computed_status for f in all_fields]
    return {
        'total': len(all_fields),
        'active': statuses.count(Field.Status.ACTIVE),
        'at_risk': statuses.count(Field.Status.AT_RISK),
        'completed': statuses.count(Field.Status.COMPLETED),
        'fields': all_fields,
    }


def get_agent_summary(agent):
    """Compute dashboard metrics for a single field agent's assigned fields."""
    # Agent dashboards reuse the same aggregate logic with a narrower queryset.
    assigned = list(
        Field.objects.filter(assigned_agent=agent)
        .prefetch_related('updates')
        .all()
    )
    statuses = [f.computed_status for f in assigned]
    return {
        'total': len(assigned),
        'active': statuses.count(Field.Status.ACTIVE),
        'at_risk': statuses.count(Field.Status.AT_RISK),
        'completed': statuses.count(Field.Status.COMPLETED),
        'fields': assigned,
    }
