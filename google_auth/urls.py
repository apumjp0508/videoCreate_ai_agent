from django.urls import path

from . import views

app_name = 'google_auth'

urlpatterns = [
    # チャンネル管理
    path('youtube/channels/', views.ChannelListView.as_view(), name='channel_list'),
    path('youtube/channels/<int:channel_id>/set-default/', views.ChannelSetDefaultView.as_view(), name='channel_set_default'),

    # OAuth フロー
    path('auth/google/start/', views.GoogleOAuthStartView.as_view(), name='oauth_start'),
    path('auth/google/callback/', views.GoogleOAuthCallbackView.as_view(), name='oauth_callback'),
]
