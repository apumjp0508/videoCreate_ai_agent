from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),

    # -----------------------------------------------------------------------
    # 動画作成フロー
    #
    # 1. /create/
    #    「動画を作成する」ボタンの遷移先。
    #    YouTubeチャンネルの有無でリダイレクト先を振り分ける。
    #    あり → YouTube選択画面 (google_auth:youtube_select)
    #    なし → YouTube連携画面 (google_auth:channel_list)
    #
    # 2. /content/select/<channel_id>/
    #    YouTube選択画面でチャンネルを選んだ後に遷移する画面。
    #    channel_id は YoutubeChannel の DB主キー（整数）。
    # -----------------------------------------------------------------------
    path('create/', views.CreateVideoView.as_view(), name='create_video'),
    path('content/select/<int:channel_id>/', views.ContentSelectView.as_view(), name='content_select'),

    # アップロード画面（content_select から遷移してくる）
    path('content/select/<int:channel_id>/image/upload/', views.ImageUploadView.as_view(), name='image_upload'),
    path('content/select/<int:channel_id>/audio/upload/', views.AudioUploadView.as_view(), name='audio_upload'),
]
