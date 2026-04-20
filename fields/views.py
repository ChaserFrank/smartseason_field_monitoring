"""Django views for browsing fields and submitting stage updates."""

from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import Http404
from .models import Field
from .forms import FieldForm, FieldUpdateForm, FieldSearchForm
from .services import filter_fields, create_field_update


class AdminRequiredMixin(LoginRequiredMixin):
    """Restricts a view to users with the admin role."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_admin_role:
            messages.error(request, 'Access denied. Admin privileges required.')
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)


class FieldListView(LoginRequiredMixin, ListView):
    """Displays searchable fields with related agent and update data."""

    model = Field
    template_name = 'fields/field_list.html'
    context_object_name = 'fields'
    paginate_by = 12

    def get_queryset(self):
        # Related data is preloaded to keep list rendering to a predictable query count.
        qs = Field.objects.select_related('assigned_agent').prefetch_related('updates')
        if self.request.user.is_field_agent:
            qs = qs.filter(assigned_agent=self.request.user)
        form = FieldSearchForm(self.request.GET)
        if form.is_valid():
            query = form.cleaned_data.get('query', '')
            stage = form.cleaned_data.get('stage', '')
            status = form.cleaned_data.get('status', '')
            return filter_fields(qs, query=query, stage=stage, status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_form'] = FieldSearchForm(self.request.GET)
        return ctx


class FieldDetailView(LoginRequiredMixin, DetailView):
    """Shows one field and its recent update history."""

    model = Field
    template_name = 'fields/field_detail.html'
    context_object_name = 'field'

    def get_object(self):
        obj = get_object_or_404(Field.objects.prefetch_related('updates__updated_by'), pk=self.kwargs['pk'])
        if self.request.user.is_field_agent and obj.assigned_agent != self.request.user:
            # Return 404 instead of 403 so other agents cannot infer field existence.
            raise Http404
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['updates'] = self.object.updates.select_related('updated_by').all()[:20]
        ctx['update_form'] = FieldUpdateForm()
        return ctx


class FieldCreateView(AdminRequiredMixin, CreateView):
    """Creates new fields for admin users."""

    model = Field
    form_class = FieldForm
    template_name = 'fields/field_form.html'
    success_url = reverse_lazy('fields:list')

    def form_valid(self, form):
        messages.success(self.request, f'Field "{form.instance.name}" created successfully.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Create New Field'
        ctx['action'] = 'Create Field'
        return ctx


class FieldEditView(AdminRequiredMixin, UpdateView):
    """Updates field metadata for admin users."""

    model = Field
    form_class = FieldForm
    template_name = 'fields/field_form.html'

    def get_success_url(self):
        return reverse_lazy('fields:detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f'Field "{form.instance.name}" updated successfully.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = f'Edit Field: {self.object.name}'
        ctx['action'] = 'Save Changes'
        return ctx


class FieldUpdateView(LoginRequiredMixin, View):
    """Handles stage update submissions for admins and assigned agents."""

    def get_field(self, pk):
        obj = get_object_or_404(Field, pk=pk)
        if self.request.user.is_field_agent and obj.assigned_agent != self.request.user:
            # Return 404 instead of 403 so other agents cannot infer field existence.
            raise Http404
        return obj

    def get(self, request, pk):
        field = self.get_field(pk)
        form = FieldUpdateForm()
        return redirect('fields:detail', pk=pk)

    def post(self, request, pk):
        field = self.get_field(pk)
        form = FieldUpdateForm(request.POST)
        if form.is_valid():
            # Stage transitions are written through the shared service layer.
            new_stage = form.cleaned_data['new_stage']
            notes = form.cleaned_data.get('notes', '')
            create_field_update(field, request.user, new_stage, notes)
            messages.success(request, f'Field "{field.name}" updated to {new_stage}.')
            return redirect('fields:detail', pk=field.pk)
        messages.error(request, 'Please correct the errors below.')
        return redirect('fields:detail', pk=pk)
