from django.contrib import admin

from .models import GeneratedAudio, GeneratedImage


@admin.register(GeneratedImage)
class GeneratedImageAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'channel', 'mime_type', 'width', 'height',
        'aspect_ratio', 'file_size_bytes', 'validation_status', 'created_at',
    )
    list_filter = ('validation_status', 'mime_type', 'aspect_ratio')
    readonly_fields = (
        'original_filename', 'mime_type', 'file_size_bytes',
        'width', 'height', 'aspect_ratio',
        'validation_status', 'validation_message',
        'created_at', 'updated_at',
    )


@admin.register(GeneratedAudio)
class GeneratedAudioAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'channel', 'mime_type', 'duration_sec',
        'sample_rate', 'channels', 'codec', 'validation_status', 'created_at',
    )
    list_filter = ('validation_status', 'mime_type', 'codec')
    readonly_fields = (
        'original_filename', 'mime_type', 'file_size_bytes',
        'duration_sec', 'sample_rate', 'channels', 'codec',
        'validation_status', 'validation_message',
        'created_at', 'updated_at',
    )
