from django.contrib import admin
from .models import Field, FieldUpdate


class FieldUpdateInline(admin.TabularInline):
    model = FieldUpdate
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    list_display = ('name', 'crop_type', 'current_stage', 'assigned_agent', 'planting_date', 'updated_at')
    list_filter = ('current_stage', 'assigned_agent')
    search_fields = ('name', 'crop_type')
    inlines = [FieldUpdateInline]


@admin.register(FieldUpdate)
class FieldUpdateAdmin(admin.ModelAdmin):
    list_display = ('field', 'updated_by', 'previous_stage', 'new_stage', 'created_at')
    list_filter = ('new_stage',)
    readonly_fields = ('created_at',)
