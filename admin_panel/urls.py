from django.urls import path

from . import views

app_name = 'admin_panel'

urlpatterns = [
    # 管理者ログイン・ログアウト
    path('login/', views.AdminLoginView.as_view(), name='login'),
    path('logout/', views.AdminLogoutView.as_view(), name='logout'),

    # ダッシュボード
    path('', views.AdminDashboardView.as_view(), name='dashboard'),

    # ユーザー管理
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/create/', views.UserCreateView.as_view(), name='user_create'),
    path('users/<int:user_id>/edit/', views.UserEditView.as_view(), name='user_edit'),
    path('users/<int:user_id>/delete/', views.UserDeleteView.as_view(), name='user_delete'),

    # AIサービス管理
    path('providers/', views.ProviderListView.as_view(), name='provider_list'),
    path('providers/create/', views.ProviderCreateView.as_view(), name='provider_create'),
    path('providers/<int:provider_id>/toggle/', views.ProviderToggleView.as_view(), name='provider_toggle'),
    path('providers/<int:provider_id>/edit/', views.ProviderEditView.as_view(), name='provider_edit'),
    path('providers/<int:provider_id>/delete/', views.ProviderDeleteView.as_view(), name='provider_delete'),
]
