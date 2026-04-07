"""
jobs アプリのモデル定義。

Django 側から見た job の正本。
画面表示・検索・絞り込み・ユーザー問い合わせ対応はここを基準にする。

テーブル構成:
  Prompt          ─ プロンプトテキスト（VideoJob から FK 参照）
  VideoJob        ─ job 本体
  VideoJobAsset   ─ job に紐づく素材（中間テーブル）
  VideoJobEvent   ─ job の履歴・イベントログ
"""
from django.conf import settings
from django.db import models


# ─────────────────────────────────────────────────────────────
# 定数
# ─────────────────────────────────────────────────────────────

class JobStatus(models.TextChoices):
    QUEUED      = 'queued',      '待機中'
    GENERATING  = 'generating',  '動画生成中'
    GENERATED   = 'generated',   '動画生成完了'
    PUBLISHING  = 'publishing',  'YouTube投稿中'
    COMPLETED   = 'completed',   '完了'
    FAILED      = 'failed',      '失敗'
    CANCELLED   = 'cancelled',   'キャンセル'


class RequestType(models.TextChoices):
    GENERATE_ONLY        = 'generate_only',        '動画生成のみ'
    GENERATE_AND_PUBLISH = 'generate_and_publish',  '動画生成 + YouTube投稿'


class JobStep(models.TextChoices):
    """current_step の選択肢。Temporal Activity の進捗と対応させる。"""
    FETCH_ASSETS       = 'FETCH_ASSETS',       '素材取得'
    FETCH_AI_CONFIG    = 'FETCH_AI_CONFIG',    'AI設定取得'
    CALL_AI            = 'CALL_AI',            'AI呼び出し'
    WAIT_AI_RESULT     = 'WAIT_AI_RESULT',     'AI生成待ち'
    FETCH_VIDEO        = 'FETCH_VIDEO',        '完成動画取得'
    FETCH_OAUTH        = 'FETCH_OAUTH',        'OAuthトークン取得'
    UPLOAD_YOUTUBE     = 'UPLOAD_YOUTUBE',     'YouTubeアップロード'
    SAVE_RESULT        = 'SAVE_RESULT',        '結果保存'


class EventType(models.TextChoices):
    JOB_CREATED             = 'JOB_CREATED',             'Job作成'
    WORKFLOW_STARTED        = 'WORKFLOW_STARTED',         'Workflow開始'
    AI_REQUEST_SENT         = 'AI_REQUEST_SENT',          'AIリクエスト送信'
    AI_RENDER_COMPLETED     = 'AI_RENDER_COMPLETED',      'AI生成完了'
    YOUTUBE_UPLOAD_STARTED  = 'YOUTUBE_UPLOAD_STARTED',   'YouTubeアップロード開始'
    YOUTUBE_UPLOAD_COMPLETED = 'YOUTUBE_UPLOAD_COMPLETED', 'YouTubeアップロード完了'
    JOB_COMPLETED           = 'JOB_COMPLETED',            'Job完了'
    JOB_FAILED              = 'JOB_FAILED',               'Job失敗'
    JOB_CANCELLED           = 'JOB_CANCELLED',            'Jobキャンセル'


class AssetRole(models.TextChoices):
    MAIN_IMAGE        = 'main_image',        'メイン画像'
    BGM               = 'bgm',               'BGM'
    NARRATION         = 'narration',         'ナレーション'
    SUBTITLE          = 'subtitle',          '字幕'
    THUMBNAIL_SOURCE  = 'thumbnail_source',  'サムネイル素材'


# ─────────────────────────────────────────────────────────────
# Prompt  ─ プロンプトテキスト
# ─────────────────────────────────────────────────────────────

class Prompt(models.Model):
    """
    ユーザーが入力したプロンプトテキストを保存するテーブル。

    VideoJob から FK で参照され、Temporal には prompt_id（PK）を渡す。
    Activity fetch_request_definition が prompt_id で DB クエリしてテキストを返す。
    将来的にはプロンプトの再利用・テンプレート化などに拡張できる。
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='prompts',
    )
    prompt_text = models.TextField()
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'prompts'

    def __str__(self):
        preview = self.prompt_text[:40].replace('\n', ' ')
        return f'Prompt #{self.pk} [{preview}...]'


# ─────────────────────────────────────────────────────────────
# VideoJob  ─ job の正本
# ─────────────────────────────────────────────────────────────

class VideoJob(models.Model):
    # ── 所有者 ───────────────────────────────────────────────
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='video_jobs',
    )

    # ── ステータス / 種別 ────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=JobStatus.choices,
        default=JobStatus.QUEUED,
        db_index=True,
    )
    request_type = models.CharField(
        max_length=30,
        choices=RequestType.choices,
        default=RequestType.GENERATE_AND_PUBLISH,
    )

    # ── コンテンツ設定 ───────────────────────────────────────
    prompt = models.ForeignKey(
        'Prompt',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='video_jobs',
    )
    credential_id = models.IntegerField(
        null=True, blank=True,
        help_text='user_video_ai_credentials の id',
    )
    model_id = models.IntegerField(
        null=True, blank=True,
        help_text='video_ai_models の id',
    )
    publish_mode = models.CharField(max_length=20, default='private')

    # ── YouTube 連携 ─────────────────────────────────────────
    google_account = models.ForeignKey(
        'google_auth.UserGoogleAccount',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='video_jobs',
    )
    youtube_channel = models.ForeignKey(
        'google_auth.YoutubeChannel',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='video_jobs',
    )

    # ── Temporal 追跡 ────────────────────────────────────────
    temporal_workflow_id = models.CharField(max_length=255, blank=True, db_index=True)
    temporal_run_id      = models.CharField(max_length=255, blank=True)

    # ── 進捗 ─────────────────────────────────────────────────
    current_step = models.CharField(
        max_length=30,
        choices=JobStep.choices,
        blank=True,
    )

    # ── エラー情報 ───────────────────────────────────────────
    error_code    = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)

    # ── タイムスタンプ ───────────────────────────────────────
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)
    started_at    = models.DateTimeField(null=True, blank=True)
    completed_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'video_jobs'
        ordering = ['-created_at']

    def __str__(self):
        return f'VideoJob #{self.pk} [{self.status}] user={self.user_id}'


# ─────────────────────────────────────────────────────────────
# VideoJobAsset  ─ job に紐づく素材（中間テーブル）
# ─────────────────────────────────────────────────────────────

class VideoJobAsset(models.Model):
    """
    job と素材の多対多中間テーブル。
    asset_id は各素材テーブルの PK を想定（画像・音声など）。
    素材点数が増えても VideoJob 本体を変更せずに対応できる。
    Temporal Workflow には asset_id のリストだけを渡し、
    実データは Activity 側で読む。
    """
    job = models.ForeignKey(
        VideoJob,
        on_delete=models.CASCADE,
        related_name='assets',
    )
    asset_id = models.IntegerField(help_text='各素材テーブルの PK')
    asset_role = models.CharField(
        max_length=30,
        choices=AssetRole.choices,
    )

    class Meta:
        db_table = 'video_job_assets'
        ordering = ['id']

    def __str__(self):
        return f'Asset job={self.job_id} role={self.asset_role} asset_id={self.asset_id}'


# ─────────────────────────────────────────────────────────────
# VideoJobEvent  ─ job の履歴・イベントログ
# ─────────────────────────────────────────────────────────────

class VideoJobEvent(models.Model):
    """
    job の状態遷移・エラー・各ステップの記録。
    Temporal への投入時・各 Activity 完了時・失敗時に Django 側から書き込む。
    削除・更新はせず追記のみ（イベントソーシング的に扱う）。
    """
    job = models.ForeignKey(
        VideoJob,
        on_delete=models.CASCADE,
        related_name='events',
    )
    event_type = models.CharField(
        max_length=40,
        choices=EventType.choices,
        db_index=True,
    )
    step_name    = models.CharField(max_length=30, blank=True)
    message      = models.TextField(blank=True)
    payload_json = models.JSONField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'video_job_events'
        ordering = ['created_at']

    def __str__(self):
        return f'Event job={self.job_id} type={self.event_type}'
