"""Forms for managing fields, stage updates, and search filters."""

from django import forms
from .models import Field, FieldUpdate
from accounts.models import User


class FieldForm(forms.ModelForm):
    """Admin form for creating and editing field metadata."""

    class Meta:
        model = Field
        fields = ['name', 'crop_type', 'planting_date', 'current_stage', 'assigned_agent']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. North Plot A'}),
            'crop_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Maize, Wheat, Tomato'}),
            'planting_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'current_stage': forms.Select(attrs={'class': 'form-select'}),
            'assigned_agent': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only active field agents should be assignable to new or edited fields.
        self.fields['assigned_agent'].queryset = User.objects.filter(role=User.Role.FIELD_AGENT, is_active=True)
        self.fields['assigned_agent'].empty_label = '— Unassigned —'
        self.fields['assigned_agent'].required = False


class FieldUpdateForm(forms.ModelForm):
    """Captures the next stage and notes for a field update."""

    class Meta:
        model = FieldUpdate
        fields = ['new_stage', 'notes']
        widgets = {
            'new_stage': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe current field conditions, observations, or any concerns...',
            }),
        }
        labels = {
            'new_stage': 'Update Stage To',
            'notes': 'Observations & Notes',
        }


class FieldSearchForm(forms.Form):
    """Filters field lists by search text, stage, and computed status."""

    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name or crop type...',
        })
    )
    stage = forms.ChoiceField(
        required=False,
        choices=[('', 'All Stages')] + list(Field.Stage.choices),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + list(Field.Status.choices),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
