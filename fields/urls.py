from django.urls import path
from . import views

app_name = 'fields'

urlpatterns = [
    path('', views.FieldListView.as_view(), name='list'),
    path('create/', views.FieldCreateView.as_view(), name='create'),
    path('<int:pk>/', views.FieldDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.FieldEditView.as_view(), name='edit'),
    path('<int:pk>/update/', views.FieldUpdateView.as_view(), name='update'),
]
