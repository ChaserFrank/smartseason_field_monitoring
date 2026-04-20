from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('login/', views.LoginAPIView.as_view(), name='login'),
    path('fields/', views.FieldListCreateAPIView.as_view(), name='field-list'),
    path('fields/<int:pk>/', views.FieldDetailAPIView.as_view(), name='field-detail'),
    path('fields/<int:pk>/updates/', views.FieldUpdateCreateAPIView.as_view(), name='field-updates'),
    path('dashboard/admin/', views.AdminDashboardAPIView.as_view(), name='admin-dashboard'),
    path('dashboard/agent/', views.AgentDashboardAPIView.as_view(), name='agent-dashboard'),
]
