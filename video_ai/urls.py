from django.urls import path

from . import views

app_name = 'video_ai'

urlpatterns = [
    path('', views.ProviderListView.as_view(), name='provider_list'),
    path('<int:provider_id>/register/', views.CredentialRegisterView.as_view(), name='credential_register'),
    path('<int:provider_id>/credential/', views.CredentialDetailView.as_view(), name='credential_detail'),
    path('<int:provider_id>/credential/update/', views.CredentialUpdateView.as_view(), name='credential_update'),
    path('<int:provider_id>/config/create/', views.ConfigCreateView.as_view(), name='config_create'),
    path('<int:provider_id>/config/<int:config_id>/update/', views.ConfigUpdateView.as_view(), name='config_update'),
]
