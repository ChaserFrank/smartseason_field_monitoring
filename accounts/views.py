"""Login and logout views for the SmartSeason web interface."""

from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.views import View
from django.shortcuts import redirect
from .forms import LoginForm


class CustomLoginView(LoginView):
    """Uses the project-specific login form and redirect behavior."""

    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return '/dashboard/'


class LogoutView(View):
    """Logs the current session out from both GET and POST requests."""

    def post(self, request):
        logout(request)
        return redirect('accounts:login')

    def get(self, request):
        logout(request)
        return redirect('accounts:login')
