from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.http import HttpResponse

# Health check endpoint for Render
def health_check(request):
    return HttpResponse("OK", status=200)

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
    path('accounts/', include('accounts.urls')),
    path('fields/', include('fields.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('api/', include('api.urls')),
]