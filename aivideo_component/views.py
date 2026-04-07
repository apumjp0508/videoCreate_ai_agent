import logging
import traceback

from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

logger = logging.getLogger(__name__)

from google_auth.models import YoutubeChannel
from jobs.services import VideoAiConfigNotFoundError, WorkflowStartError, create_video_job, start_workflow_for_job
from .forms import (
    AudioEditForm, AudioUploadForm,
    ContentSelectForm,
    ImageEditForm, ImageUploadForm,
    AIProviderSelectForm,
)
from .metadata.service import apply_audio_metadata, apply_image_metadata
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
            instance = GeneratedImage.objects.create(
                youtube_channel=channel,
                title=form.cleaned_data['title'],
                image_file=form.cleaned_data['file'],
            )
            apply_image_metadata(instance, form.cleaned_data['file'])
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
            new_file = form.cleaned_data.get('file')
            if new_file:
                # 古いファイルをストレージから削除してから差し替え
                image.image_file.delete(save=False)
                image.image_file = new_file
            image.save()
            if new_file:
                apply_image_metadata(image, new_file)
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
            instance = GeneratedAudio.objects.create(
                youtube_channel=channel,
                title=form.cleaned_data['title'],
                audio_file=form.cleaned_data['file'],
            )
            apply_audio_metadata(instance, form.cleaned_data['file'])
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
            new_file = form.cleaned_data.get('file')
            if new_file:
                audio.audio_file.delete(save=False)
                audio.audio_file = new_file
            audio.save()
            if new_file:
                apply_audio_metadata(audio, new_file)
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
    動画生成に使う AI プロバイダとモデルを選択する画面（動画作成ステップ3）。
    """

    def _build_choices(self, request):
        """
        ユーザーの登録済み credential と管理者が有効にした VideoAiModel から
        フォーム用の choices と補助情報を組み立てる。

        Returns:
            provider_choices    : [(provider_key, name), ...]
            model_choices       : [(str(model_id), model_name), ...]
            credential_map      : {provider_key: credential_id}
            models_by_provider  : {provider_key: [VideoAiModel, ...]}
        """
        from video_ai.models import UserVideoAiCredential, VideoAiModel

        credentials = (
            UserVideoAiCredential.objects
            .filter(user=request.user, is_active=True)
            .select_related('provider')
        )

        credential_map = {c.provider.provider_key: c.id for c in credentials}
        provider_ids = [c.provider_id for c in credentials]

        provider_choices = [
            (c.provider.provider_key, c.provider.provider_name)
            for c in credentials
        ]

        active_models = (
            VideoAiModel.objects
            .filter(provider_id__in=provider_ids, is_active=True)
            .select_related('provider')
            .order_by('provider__provider_name', 'model_name')
        )

        model_choices = [(str(m.id), m.model_name) for m in active_models]

        models_by_provider: dict = {}
        for m in active_models:
            models_by_provider.setdefault(m.provider.provider_key, []).append(m)

        return provider_choices, model_choices, credential_map, models_by_provider

    def _build_provider_data(self, request):
        """テンプレートに渡す provider リスト（models 付き）を組み立てる。"""
        from video_ai.models import UserVideoAiCredential, VideoAiModel

        credentials = (
            UserVideoAiCredential.objects
            .filter(user=request.user, is_active=True)
            .select_related('provider')
        )

        provider_data = []
        for c in credentials:
            models = list(
                VideoAiModel.objects
                .filter(provider=c.provider, is_active=True)
                .order_by('model_name')
            )
            provider_data.append({
                'id':            c.provider.provider_key,
                'name':          c.provider.provider_name,
                'credential_id': c.id,
                'models':        models,
                'status':        None,
                'message':       None,
                'errors':        [],
                'warnings':      [],
            })

        # ── コンテンツ選択済みなら事前バリデーション ─────────────────
        # ページロード時に各プロバイダーの適合状態を先読みして表示する。
        # 失敗しても画面は壊さない（try/except で無視）。
        selection = request.session.get(_CONTENT_SELECTION_SESSION_KEY, {})
        if selection:
            for p in provider_data:
                try:
                    validation_input = self._build_validation_input(p['id'], selection)
                    result = validate_content(validation_input)
                    if result.is_unsupported:
                        p['status'] = 'unavailable'
                        p['errors'] = [e.message for e in result.errors]
                    elif not result.is_valid:
                        p['status'] = 'unavailable'
                        p['errors']   = [e.message for e in result.errors]
                        p['warnings'] = [w.message for w in result.warnings]
                    elif result.warnings:
                        p['status'] = 'caution'
                        p['warnings'] = [w.message for w in result.warnings]
                    else:
                        p['status'] = 'ok'
                except Exception:
                    pass  # 事前バリデーション失敗は無視して表示を継続

        return provider_data

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
        provider_choices, model_choices, _, _ = self._build_choices(request)
        return render(request, 'aivideo_component/provider_select.html', {
            'form': AIProviderSelectForm(
                provider_choices=provider_choices,
                model_choices=model_choices,
            ),
            'providers': self._build_provider_data(request),
            'channel_id': channel_id,
        })

    def post(self, request, channel_id: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        provider_choices, model_choices, credential_map, models_by_provider = self._build_choices(request)
        form = AIProviderSelectForm(
            request.POST,
            provider_choices=provider_choices,
            model_choices=model_choices,
        )

        def _render(f):
            return render(request, 'aivideo_component/provider_select.html', {
                'form': f,
                'providers': self._build_provider_data(request),
                'channel_id': channel_id,
            })

        if not form.is_valid():
            return _render(form)

        provider_key = form.cleaned_data['provider']
        model_id     = int(form.cleaned_data['model_id'])
        credential_id = credential_map.get(provider_key)

        # モデルが選択プロバイダーに属しているか確認
        valid_model_ids = {m.id for m in models_by_provider.get(provider_key, [])}
        if model_id not in valid_model_ids:
            messages.error(request, '選択されたモデルはプロバイダーに対応していません。')
            return _render(form)

        # ── コンテンツバリデーション ──────────────────────────────
        selection = request.session.get(_CONTENT_SELECTION_SESSION_KEY, {})
        try:
            validation_input = self._build_validation_input(provider_key, selection)
            result = validate_content(validation_input)
        except UnknownProviderError as exc:
            logger.warning('UnknownProviderError: %s', exc)
            messages.error(request, '選択された AI プロバイダーは現在サポートされていません。')
            if settings.DEBUG:
                messages.error(request, f'[DEV] {traceback.format_exc()}')
            return _render(form)

        if not result.is_valid:
            for issue in result.errors:
                messages.error(request, f'[{issue.field}] {issue.message}')
            return _render(form)

        for issue in result.warnings:
            messages.warning(request, f'[{issue.field}] {issue.message}')

        # ── バリデーション通過 → Job 作成 ────────────────────────
        try:
            job = create_video_job(
                user=request.user,
                channel_id=channel_id,
                credential_id=credential_id,
                model_id=model_id,
                script=selection.get('script', ''),
                image_id=int(selection['image_id']) if selection.get('image_id') else None,
                audio_id=int(selection['audio_id']) if selection.get('audio_id') else None,
                publish_mode=selection.get('publish_mode', 'private'),
            )
        except VideoAiConfigNotFoundError as exc:
            logger.error('VideoAiConfigNotFoundError: %s', exc)
            messages.error(request, str(exc))
            if settings.DEBUG:
                messages.error(request, f'[DEV] {traceback.format_exc()}')
            return _render(form)

        # ── Temporal Workflow 起動 ────────────────────────────────
        try:
            start_workflow_for_job(job)
        except WorkflowStartError as exc:
            logger.error('WorkflowStartError job_id=%s: %s', job.id, exc)
            messages.error(request, f'動画生成の開始に失敗しました。しばらく経ってから再試行してください。（{exc}）')
            if settings.DEBUG:
                messages.error(request, f'[DEV] {traceback.format_exc()}')
            return _render(form)

        # ── 成功 → セッションをクリアして完了 ────────────────────
        request.session.pop(_CONTENT_SELECTION_SESSION_KEY, None)
        messages.success(request, f'動画生成ジョブを作成しました（Job #{job.id}）')
        return redirect('accounts:dashboard')
