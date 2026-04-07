from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from google_auth.models import YoutubeChannel
from jobs.services import VideoAiConfigNotFoundError, WorkflowStartError, create_video_job, start_workflow_for_job
from .forms import (
    AudioEditForm, AudioUploadForm,
    ContentSelectForm,
    ImageEditForm, ImageUploadForm,
    AIProviderSelectForm, AI_PROVIDERS,
)
from .models import GeneratedAudio, GeneratedImage
from .validation.protocol import AudioMeta, ContentValidationInput, ImageMeta
from .validation.registry import UnknownProviderError, validate_content

# セッションキー: ContentSelectView で保存した選択内容を AIProviderSelectView で参照する
_CONTENT_SELECTION_SESSION_KEY = 'aivideo_content_selection'


class ContentSelectView(View):
    """
    スクリプト / 画像 / 音声 を選択する画面（動画作成ステップ2）。
    画像・音声の一覧表示と CRUD 導線もここで提供する。
    """

    def _get_channel(self, request, channel_id):
        return get_object_or_404(
            YoutubeChannel,
            id=channel_id,
            user_google_account__user=request.user,
        )

    def _build_context(self, request, channel_id):
        channel = self._get_channel(request, channel_id)
        images = GeneratedImage.objects.filter(youtube_channel=channel)
        audios = GeneratedAudio.objects.filter(youtube_channel=channel)
        image_choices = [(img.pk, img.title) for img in images]
        audio_choices = [(aud.pk, aud.title) for aud in audios]
        return {
            'channel': channel,
            'channel_id': channel_id,
            'images': images,
            'audios': audios,
            'has_images': bool(image_choices),
            'has_audios': bool(audio_choices),
            'image_choices': image_choices,
            'audio_choices': audio_choices,
        }

    def get(self, request, channel_id: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        ctx = self._build_context(request, channel_id)
        ctx['form'] = ContentSelectForm(
            image_choices=ctx['image_choices'],
            audio_choices=ctx['audio_choices'],
        )
        return render(request, 'aivideo_component/content_select.html', ctx)

    def post(self, request, channel_id: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        ctx = self._build_context(request, channel_id)
        form = ContentSelectForm(
            request.POST,
            image_choices=ctx['image_choices'],
            audio_choices=ctx['audio_choices'],
        )
        if form.is_valid():
            # 選択内容をセッションに保存して AI プロバイダー選択画面へ渡す
            request.session[_CONTENT_SELECTION_SESSION_KEY] = {
                'script':       form.cleaned_data['script'],
                'image_id':     form.cleaned_data.get('image') or None,
                'audio_id':     form.cleaned_data.get('audio') or None,
                'publish_mode': form.cleaned_data['publish_mode'],
            }
            return redirect('aivideo_component:provider_select', channel_id=channel_id)
        ctx['form'] = form
        return render(request, 'aivideo_component/content_select.html', ctx)


# ─────────────────────── Image CRUD ───────────────────────

class ImageUploadView(View):
    """画像新規アップロード（Create）。"""

    def get(self, request, channel_id: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        return render(request, 'aivideo_component/image_upload.html', {
            'form': ImageUploadForm(),
            'channel_id': channel_id,
        })

    def post(self, request, channel_id: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        channel = get_object_or_404(
            YoutubeChannel,
            id=channel_id,
            user_google_account__user=request.user,
        )
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            GeneratedImage.objects.create(
                youtube_channel=channel,
                title=form.cleaned_data['title'],
                image_file=form.cleaned_data['file'],
            )
            messages.success(request, '画像を保存しました。')
            return redirect('aivideo_component:content_select', channel_id=channel_id)

        return render(request, 'aivideo_component/image_upload.html', {
            'form': form,
            'channel_id': channel_id,
        })


class ImageEditView(View):
    """画像タイトル・ファイルの編集（Update）。"""

    def _get_image(self, request, channel_id, pk):
        return get_object_or_404(
            GeneratedImage,
            pk=pk,
            youtube_channel__id=channel_id,
            youtube_channel__user_google_account__user=request.user,
        )

    def get(self, request, channel_id: int, pk: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        image = self._get_image(request, channel_id, pk)
        form = ImageEditForm(initial={'title': image.title})
        return render(request, 'aivideo_component/image_edit.html', {
            'form': form,
            'channel_id': channel_id,
            'image': image,
        })

    def post(self, request, channel_id: int, pk: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        image = self._get_image(request, channel_id, pk)
        form = ImageEditForm(request.POST, request.FILES)
        if form.is_valid():
            image.title = form.cleaned_data['title']
            if form.cleaned_data.get('file'):
                # 古いファイルをストレージから削除してから差し替え
                image.image_file.delete(save=False)
                image.image_file = form.cleaned_data['file']
            image.save()
            messages.success(request, '画像を更新しました。')
            return redirect('aivideo_component:content_select', channel_id=channel_id)

        return render(request, 'aivideo_component/image_edit.html', {
            'form': form,
            'channel_id': channel_id,
            'image': image,
        })


class ImageDeleteView(View):
    """画像削除確認 → 削除（Delete）。"""

    def _get_image(self, request, channel_id, pk):
        return get_object_or_404(
            GeneratedImage,
            pk=pk,
            youtube_channel__id=channel_id,
            youtube_channel__user_google_account__user=request.user,
        )

    def get(self, request, channel_id: int, pk: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        image = self._get_image(request, channel_id, pk)
        return render(request, 'aivideo_component/image_delete.html', {
            'channel_id': channel_id,
            'image': image,
        })

    def post(self, request, channel_id: int, pk: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        image = self._get_image(request, channel_id, pk)
        image.image_file.delete(save=False)
        image.delete()
        messages.success(request, '画像を削除しました。')
        return redirect('aivideo_component:content_select', channel_id=channel_id)


# ─────────────────────── Audio CRUD ───────────────────────

class AudioUploadView(View):
    """音声新規アップロード（Create）。"""

    def get(self, request, channel_id: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        return render(request, 'aivideo_component/audio_upload.html', {
            'form': AudioUploadForm(),
            'channel_id': channel_id,
        })

    def post(self, request, channel_id: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        channel = get_object_or_404(
            YoutubeChannel,
            id=channel_id,
            user_google_account__user=request.user,
        )
        form = AudioUploadForm(request.POST, request.FILES)
        if form.is_valid():
            GeneratedAudio.objects.create(
                youtube_channel=channel,
                title=form.cleaned_data['title'],
                audio_file=form.cleaned_data['file'],
            )
            messages.success(request, '音声を保存しました。')
            return redirect('aivideo_component:content_select', channel_id=channel_id)

        return render(request, 'aivideo_component/audio_upload.html', {
            'form': form,
            'channel_id': channel_id,
        })


class AudioEditView(View):
    """音声タイトル・ファイルの編集（Update）。"""

    def _get_audio(self, request, channel_id, pk):
        return get_object_or_404(
            GeneratedAudio,
            pk=pk,
            youtube_channel__id=channel_id,
            youtube_channel__user_google_account__user=request.user,
        )

    def get(self, request, channel_id: int, pk: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        audio = self._get_audio(request, channel_id, pk)
        form = AudioEditForm(initial={'title': audio.title})
        return render(request, 'aivideo_component/audio_edit.html', {
            'form': form,
            'channel_id': channel_id,
            'audio': audio,
        })

    def post(self, request, channel_id: int, pk: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        audio = self._get_audio(request, channel_id, pk)
        form = AudioEditForm(request.POST, request.FILES)
        if form.is_valid():
            audio.title = form.cleaned_data['title']
            if form.cleaned_data.get('file'):
                audio.audio_file.delete(save=False)
                audio.audio_file = form.cleaned_data['file']
            audio.save()
            messages.success(request, '音声を更新しました。')
            return redirect('aivideo_component:content_select', channel_id=channel_id)

        return render(request, 'aivideo_component/audio_edit.html', {
            'form': form,
            'channel_id': channel_id,
            'audio': audio,
        })


class AudioDeleteView(View):
    """音声削除確認 → 削除（Delete）。"""

    def _get_audio(self, request, channel_id, pk):
        return get_object_or_404(
            GeneratedAudio,
            pk=pk,
            youtube_channel__id=channel_id,
            youtube_channel__user_google_account__user=request.user,
        )

    def get(self, request, channel_id: int, pk: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        audio = self._get_audio(request, channel_id, pk)
        return render(request, 'aivideo_component/audio_delete.html', {
            'channel_id': channel_id,
            'audio': audio,
        })

    def post(self, request, channel_id: int, pk: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        audio = self._get_audio(request, channel_id, pk)
        audio.audio_file.delete(save=False)
        audio.delete()
        messages.success(request, '音声を削除しました。')
        return redirect('aivideo_component:content_select', channel_id=channel_id)


# ─────────────────────── AI Provider Select ───────────────────────

class AIProviderSelectView(View):
    """
    動画生成に使う AI プロバイダを選択する画面（動画作成ステップ3）。

    現時点はフォーム表示のみ。将来の拡張ポイント:
      - providers に status / message を付与して適合判定を表示
      - POST 処理で動画生成ジョブを作成
    """

    def _build_providers(self):
        """
        テンプレートに渡す provider リストを組み立てる。
        将来は画像・音声のメタ情報を元に status / message を付与する。
        例: {'id': 'runway', 'name': 'Runway', 'status': 'ok', 'message': '使用可能'}
        """
        return [
            {**p, 'status': None, 'message': None}
            for p in AI_PROVIDERS
        ]

    def _build_validation_input(
        self,
        provider_key: str,
        selection: dict,
    ) -> ContentValidationInput:
        """
        セッションの選択内容と provider_key から ContentValidationInput を組み立てる。
        モデルから必要なメタデータを取得してバリデーター用の型に変換する。
        """
        image_meta = None
        if selection.get('image_id'):
            try:
                img = GeneratedImage.objects.get(pk=selection['image_id'])
                image_meta = ImageMeta(
                    image_id=img.pk,
                    mime_type=img.mime_type,
                    file_size_bytes=img.file_size_bytes,
                    width=img.width,
                    height=img.height,
                    aspect_ratio=img.aspect_ratio,
                )
            except GeneratedImage.DoesNotExist:
                pass

        audio_meta = None
        if selection.get('audio_id'):
            try:
                aud = GeneratedAudio.objects.get(pk=selection['audio_id'])
                audio_meta = AudioMeta(
                    audio_id=aud.pk,
                    mime_type=aud.mime_type,
                    file_size_bytes=aud.file_size_bytes,
                    duration_sec=aud.duration_sec,
                    sample_rate=aud.sample_rate,
                    channels=aud.channels,
                    codec=aud.codec,
                )
            except GeneratedAudio.DoesNotExist:
                pass

        return ContentValidationInput(
            provider_key=provider_key,
            script=selection.get('script', ''),
            image=image_meta,
            audio=audio_meta,
        )

    def get(self, request, channel_id: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        return render(request, 'aivideo_component/provider_select.html', {
            'form': AIProviderSelectForm(),
            'providers': self._build_providers(),
            'channel_id': channel_id,
        })

    def post(self, request, channel_id: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        form = AIProviderSelectForm(request.POST)
        if not form.is_valid():
            return render(request, 'aivideo_component/provider_select.html', {
                'form': form,
                'providers': self._build_providers(),
                'channel_id': channel_id,
            })

        provider_key = form.cleaned_data['provider']

        # ── コンテンツバリデーション ──────────────────────────────
        selection = request.session.get(_CONTENT_SELECTION_SESSION_KEY, {})
        try:
            validation_input = self._build_validation_input(provider_key, selection)
            result = validate_content(validation_input)
        except UnknownProviderError:
            messages.error(request, '選択された AI プロバイダーは現在サポートされていません。')
            return render(request, 'aivideo_component/provider_select.html', {
                'form': form,
                'providers': self._build_providers(),
                'channel_id': channel_id,
            })

        if not result.is_valid:
            for issue in result.errors:
                messages.error(request, f'[{issue.field}] {issue.message}')
            return render(request, 'aivideo_component/provider_select.html', {
                'form': form,
                'providers': self._build_providers(),
                'channel_id': channel_id,
            })

        for issue in result.warnings:
            messages.warning(request, f'[{issue.field}] {issue.message}')

        # ── バリデーション通過 → Job 作成 ────────────────────────
        try:
            job = create_video_job(
                user=request.user,
                channel_id=channel_id,
                provider_key=provider_key,
                script=selection.get('script', ''),
                image_id=int(selection['image_id']) if selection.get('image_id') else None,
                audio_id=int(selection['audio_id']) if selection.get('audio_id') else None,
                publish_mode=selection.get('publish_mode', 'private'),
            )
        except VideoAiConfigNotFoundError as exc:
            messages.error(request, str(exc))
            return render(request, 'aivideo_component/provider_select.html', {
                'form': form,
                'providers': self._build_providers(),
                'channel_id': channel_id,
            })

        # ── Temporal Workflow 起動 ────────────────────────────────
        try:
            start_workflow_for_job(job)
        except WorkflowStartError as exc:
            messages.error(request, f'動画生成の開始に失敗しました。しばらく経ってから再試行してください。（{exc}）')
            return render(request, 'aivideo_component/provider_select.html', {
                'form': form,
                'providers': self._build_providers(),
                'channel_id': channel_id,
            })

        # ── 成功 → セッションをクリアして完了 ────────────────────
        request.session.pop(_CONTENT_SELECTION_SESSION_KEY, None)
        messages.success(request, f'動画生成ジョブを作成しました（Job #{job.id}）')
        return redirect('accounts:dashboard')
