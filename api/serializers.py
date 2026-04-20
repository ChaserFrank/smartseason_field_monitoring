"""DRF serializers for field, update, and dashboard payloads."""

from rest_framework import serializers
from fields.models import Field, FieldUpdate
from accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializes the subset of user data exposed by the API."""

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'role']


class FieldUpdateSerializer(serializers.ModelSerializer):
    """Serializes audit records with the updater nested for readability."""

    updated_by = UserSerializer(read_only=True)

    class Meta:
        model = FieldUpdate
        fields = ['id', 'field', 'updated_by', 'previous_stage', 'new_stage', 'notes', 'created_at']
        read_only_fields = ['previous_stage', 'updated_by', 'created_at']


class FieldSerializer(serializers.ModelSerializer):
    """Serializes fields together with derived status and recent activity."""

    assigned_agent = UserSerializer(read_only=True)
    assigned_agent_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=User.Role.FIELD_AGENT),
        source='assigned_agent',
        write_only=True,
        required=False,
        allow_null=True,
    )
    computed_status = serializers.ReadOnlyField()
    stage_progress = serializers.ReadOnlyField()
    days_since_planted = serializers.ReadOnlyField()
    latest_update = serializers.SerializerMethodField()

    class Meta:
        model = Field
        fields = [
            'id', 'name', 'crop_type', 'planting_date', 'current_stage',
            'assigned_agent', 'assigned_agent_id', 'computed_status',
            'stage_progress', 'days_since_planted', 'latest_update',
            'created_at', 'updated_at',
        ]

    def get_latest_update(self, obj):
        # The latest update is embedded so clients do not need a second request.
        update = obj.updates.order_by('-created_at').first()
        if update:
            return FieldUpdateSerializer(update).data
        return None


class CreateFieldUpdateSerializer(serializers.ModelSerializer):
    """Validates the minimal payload needed to create a new stage update."""

    class Meta:
        model = FieldUpdate
        fields = ['new_stage', 'notes']

    def validate_new_stage(self, value):
        if value not in dict(Field.Stage.choices):
            raise serializers.ValidationError('Invalid stage.')
        return value
