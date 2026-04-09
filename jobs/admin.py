from django.contrib import admin
from django.utils.html import format_html

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
    list_display = (
        'id', 'user', 'status', 'request_type', 'current_step',
        'error_summary', 'created_at', 'completed_at',
    )
    list_filter = ('status', 'request_type')
    search_fields = ('user__email', 'temporal_workflow_id', 'error_code')
    readonly_fields = (
        'temporal_workflow_id', 'temporal_run_id',
        'created_at', 'updated_at',
        'error_detail_display',
    )
    fieldsets = (
        ('基本情報', {
            'fields': ('user', 'status', 'request_type', 'current_step'),
        }),
        ('コンテンツ設定', {
            'fields': ('prompt', 'credential_id', 'model_id', 'publish_mode', 'video_length'),
        }),
        ('YouTube連携', {
            'fields': ('google_account', 'youtube_channel', 'youtube_video_id', 'youtube_video_url'),
        }),
        ('エラー情報', {
            'fields': ('error_code', 'error_message', 'error_detail_display'),
            'classes': ('collapse',),
            'description': 'Workflowが失敗した場合のエラー詳細。cause_chain で根本原因の連鎖を確認できます。',
        }),
        ('Temporal', {
            'fields': ('temporal_workflow_id', 'temporal_run_id'),
            'classes': ('collapse',),
        }),
        ('タイムスタンプ', {
            'fields': ('created_at', 'updated_at', 'started_at', 'completed_at'),
            'classes': ('collapse',),
        }),
    )
    inlines = [VideoJobAssetInline, VideoJobEventInline]

    @admin.display(description='エラー概要')
    def error_summary(self, obj):
        if obj.error_code:
            return format_html(
                '<span style="color:red;">[{}] {}</span>',
                obj.error_code,
                (obj.error_message or '')[:60],
            )
        return '-'

    @admin.display(description='エラー詳細（cause_chain）')
    def error_detail_display(self, obj):
        """JOB_FAILED イベントの payload_json.cause_chain を整形表示する。"""
        failed_event = (
            obj.events.filter(event_type='JOB_FAILED')
            .order_by('-created_at')
            .first()
        )
        if not failed_event or not failed_event.payload_json:
            return '-'

        cause_chain = failed_event.payload_json.get('cause_chain', [])
        if not cause_chain:
            return failed_event.payload_json.get('error_detail', '-')

        lines = '<br>'.join(
            format_html('&nbsp;&nbsp;' * i + '↳ {}', entry)
            for i, entry in enumerate(cause_chain)
        )
        return format_html('<code style="font-size:0.85em;">{}</code>', format_html(lines))


@admin.register(VideoJobEvent)
class VideoJobEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'job', 'event_type', 'step_name', 'message_preview', 'created_at')
    list_filter = ('event_type',)
    search_fields = ('job__id', 'message')
    readonly_fields = ('job', 'event_type', 'step_name', 'message', 'payload_json', 'created_at')

    @admin.display(description='メッセージ')
    def message_preview(self, obj):
        msg = obj.message or ''
        if len(msg) > 80:
            return msg[:80] + '…'
        return msg
