from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from google_auth.models import YoutubeChannel
from .forms import (
    AudioEditForm, AudioUploadForm,
    ContentSelectForm,
    ImageEditForm, ImageUploadForm,
)
from .models import GeneratedAudio, GeneratedImage


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
            # TODO: 動画生成ジョブ作成処理をここに追加する
            return redirect('accounts:dashboard')
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
