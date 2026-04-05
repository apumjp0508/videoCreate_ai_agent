from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),

    # -----------------------------------------------------------------------
    # 動画作成フロー（channel選択 → コンテンツ選択）
    #
    # 現在はchannel選択画面が未完成のため、channel_id を URLパラメータで直接受け取る。
    # 単体確認: /content/select/1/ のように直接アクセスできる。
    #
    # TODO: channel選択画面が完成したら、そちらのフォーム送信先を
    #       redirect('accounts:content_select', channel_id=選択されたID) に向けるだけでOK。
    # -----------------------------------------------------------------------
    path('content/select/<int:channel_id>/', views.ContentSelectView.as_view(), name='content_select'),

    # アップロード画面（content_select から遷移してくる）
    path('content/select/<int:channel_id>/image/upload/', views.ImageUploadView.as_view(), name='image_upload'),
    path('content/select/<int:channel_id>/audio/upload/', views.AudioUploadView.as_view(), name='audio_upload'),
]
