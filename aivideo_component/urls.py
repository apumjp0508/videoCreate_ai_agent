from django.urls import path

from . import views

app_name = 'aivideo_component'

urlpatterns = [
    # 動画作成フロー ステップ2: コンテンツ選択（一覧兼操作ハブ）
    path('content/select/<int:channel_id>/', views.ContentSelectView.as_view(), name='content_select'),

    # 画像 CRUD
    path('content/select/<int:channel_id>/image/upload/', views.ImageUploadView.as_view(), name='image_upload'),
    path('content/select/<int:channel_id>/image/<int:pk>/edit/', views.ImageEditView.as_view(), name='image_edit'),
    path('content/select/<int:channel_id>/image/<int:pk>/delete/', views.ImageDeleteView.as_view(), name='image_delete'),

    # 音声 CRUD
    path('content/select/<int:channel_id>/audio/upload/', views.AudioUploadView.as_view(), name='audio_upload'),
    path('content/select/<int:channel_id>/audio/<int:pk>/edit/', views.AudioEditView.as_view(), name='audio_edit'),
    path('content/select/<int:channel_id>/audio/<int:pk>/delete/', views.AudioDeleteView.as_view(), name='audio_delete'),

    # 動画作成フロー ステップ3: 生成AI選択
    path('content/select/<int:channel_id>/provider/select/', views.AIProviderSelectView.as_view(), name='provider_select'),
]
