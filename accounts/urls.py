from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('register/connect-google/', views.RegisterConnectGoogleView.as_view(), name='register_connect_google'),
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
    # 2. コンテンツ選択・アップロード画面は aivideo_component app が担当。
    #    → aivideo_component:content_select / image_upload / audio_upload
    # -----------------------------------------------------------------------
    path('create/', views.CreateVideoView.as_view(), name='create_video'),
]
