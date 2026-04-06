from django.contrib import admin

from .models import VideoJob, VideoJobAsset, VideoJobEvent


class VideoJobAssetInline(admin.TabularInline):
    model = VideoJobAsset
    extra = 0


class VideoJobEventInline(admin.TabularInline):
    model = VideoJobEvent
    extra = 0
    readonly_fields = ('event_type', 'step_name', 'message', 'payload_json', 'created_at')
    can_delete = False


@admin.register(VideoJob)
class VideoJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'request_type', 'current_step', 'created_at', 'completed_at')
    list_filter = ('status', 'request_type')
    search_fields = ('user__email', 'temporal_workflow_id', 'error_code')
    readonly_fields = ('temporal_workflow_id', 'temporal_run_id', 'created_at', 'updated_at')
    inlines = [VideoJobAssetInline, VideoJobEventInline]


@admin.register(VideoJobEvent)
class VideoJobEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'job', 'event_type', 'step_name', 'created_at')
    list_filter = ('event_type',)
    search_fields = ('job__id',)
    readonly_fields = ('job', 'event_type', 'step_name', 'message', 'payload_json', 'created_at')
