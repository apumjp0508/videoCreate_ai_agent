from django.contrib import admin

from video_ai.models import UserVideoAiCredential, VideoAiModel, VideoAiProvider


@admin.register(VideoAiProvider)
class VideoAiProviderAdmin(admin.ModelAdmin):
    list_display = ('id', 'provider_key', 'provider_name', 'api_base_url', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('provider_key', 'provider_name')


@admin.register(VideoAiModel)
class VideoAiModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'provider', 'model_name', 'is_active')
    list_filter = ('is_active', 'provider')
    search_fields = ('model_name', 'provider__provider_name')
    list_editable = ('is_active',)


@admin.register(UserVideoAiCredential)
class UserVideoAiCredentialAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'provider', 'test_status', 'is_active', 'created_at')
    list_filter = ('is_active', 'test_status', 'provider')
    search_fields = ('user__email', 'provider__provider_name')
    readonly_fields = ('created_at', 'updated_at')


