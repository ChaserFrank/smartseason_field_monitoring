"""Dashboard views that aggregate field metrics for admins and agents."""

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from fields.models import Field, FieldUpdate
from fields.services import get_admin_summary, get_agent_summary
from accounts.models import User


class DashboardHomeView(LoginRequiredMixin, TemplateView):
    """Renders the role-specific dashboard with shared summary metrics."""

    def get_template_names(self):
        if self.request.user.is_admin_role:
            return ['dashboard/admin_dashboard.html']
        return ['dashboard/agent_dashboard.html']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        if user.is_admin_role:
            summary = get_admin_summary()
            ctx.update(summary)

            # Recent fields and updates are preloaded to keep the dashboard responsive.
            ctx['recent_fields'] = Field.objects.select_related('assigned_agent') \
                .prefetch_related('updates').order_by('-updated_at')[:6]

            # This grouped summary is used to compare field-agent visibility at a glance.
            agents = User.objects.filter(role=User.Role.FIELD_AGENT, is_active=True) \
                .prefetch_related('assigned_fields__updates')
            agent_data = []
            for agent in agents:
                agent_fields = list(agent.assigned_fields.all())
                agent_data.append({
                    'agent': agent,
                    'total': len(agent_fields),
                    'at_risk': sum(1 for f in agent_fields if f.computed_status == Field.Status.AT_RISK),
                    'completed': sum(1 for f in agent_fields if f.computed_status == Field.Status.COMPLETED),
                })
            ctx['agent_data'] = agent_data
            ctx['recent_updates'] = FieldUpdate.objects.select_related('field', 'updated_by').order_by('-created_at')[:8]

        else:
            summary = get_agent_summary(user)
            ctx.update(summary)
            # Agents only see their own updates, so the queryset is scoped accordingly.
            ctx['recent_updates'] = FieldUpdate.objects.filter(
                field__assigned_agent=user
            ).select_related('field', 'updated_by').order_by('-created_at')[:6]

        return ctx


class DashboardRedirectView(LoginRequiredMixin, TemplateView):
    """Redirects authenticated users to the main dashboard entry point."""

    def get(self, request, *args, **kwargs):
        return redirect('dashboard:home')
