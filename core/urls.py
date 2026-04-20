from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
    path('accounts/', include('accounts.urls')),
    path('fields/', include('fields.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('api/', include('api.urls')),
]
