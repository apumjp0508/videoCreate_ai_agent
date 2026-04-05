from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .forms import AudioUploadForm, ContentSelectForm, ImageUploadForm, LoginForm, RegisterForm
from .dummy_data import get_audio_choices, get_image_choices
from google_auth.models import YoutubeChannel


class RegisterView(View):
    def get(self, request):
        form = RegisterForm()
        return render(request, 'accounts/register.html', {'form': form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('accounts:dashboard')
        return render(request, 'accounts/register.html', {'form': form})


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return '/dashboard/'


class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('accounts:login')


class DashboardView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        return render(request, 'accounts/dashboard.html')


class CreateVideoView(View):
    """
    「動画を作成する」押下時の分岐ビュー。

    ログイン中ユーザーに紐づくYouTubeチャンネルの有無で遷移先を振り分ける。
    - チャンネルあり → YouTube選択画面 (google_auth:youtube_select)
    - チャンネルなし → YouTube連携画面 (google_auth:channel_list)
    """

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        # ログイン中ユーザーのアクティブなYouTubeチャンネルを確認
        has_channels = YoutubeChannel.objects.filter(
            user_google_account__user=request.user,
            is_active=True,
        ).exists()

        if has_channels:
            return redirect('google_auth:youtube_select')
        return redirect('google_auth:channel_list')


class ContentSelectView(View):
    """
    スクリプト / 画像 / 音声 を選択する画面（動画作成ステップ2）。

    URLパラメータ channel_id は YoutubeChannel の DB主キー（整数）。
    YouTube選択画面で選んだチャンネルの channel.id がここに渡される。
    """

    def get(self, request, channel_id: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        # DBからチャンネル情報を取得（ログイン中ユーザーのチャンネルのみ許可）
        channel = get_object_or_404(
            YoutubeChannel,
            id=channel_id,
            user_google_account__user=request.user,
        )

        image_choices = get_image_choices(channel_id)
        audio_choices = get_audio_choices(channel_id)

        form = ContentSelectForm(
            image_choices=image_choices,
            audio_choices=audio_choices,
        )

        context = {
            'form': form,
            'channel_id': channel_id,
            'channel': channel,
        }
        return render(request, 'accounts/content_select.html', context)

    def post(self, request, channel_id: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        channel = get_object_or_404(
            YoutubeChannel,
            id=channel_id,
            user_google_account__user=request.user,
        )
        image_choices = get_image_choices(channel_id)
        audio_choices = get_audio_choices(channel_id)

        form = ContentSelectForm(
            request.POST,
            image_choices=image_choices,
            audio_choices=audio_choices,
        )

        if form.is_valid():
            # TODO: バリデーション通過後の処理（動画生成ジョブ作成など）をここに書く
            # 現時点ではダッシュボードへリダイレクト（仮）
            return redirect('accounts:dashboard')

        context = {
            'form': form,
            'channel_id': channel_id,
            'channel': channel,
        }
        return render(request, 'accounts/content_select.html', context)


class ImageUploadView(View):
    """
    画像アップロード画面。

    今回はUI・遷移の骨組みのみ。送信後は「仮送信完了」メッセージを同画面に表示する。
    TODO: DB完成後に form.cleaned_data を使って画像メタ情報を保存する
    TODO: 実ファイル保存処理（storage への書き込み）を追加する
    TODO: channel_id や user と紐づける処理を追加する
    """

    def get(self, request, channel_id: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        form = ImageUploadForm()
        return render(request, 'accounts/image_upload.html', {
            'form': form,
            'channel_id': channel_id,
            'uploaded': False,
        })

    def post(self, request, channel_id: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # TODO: DB完成後に画像メタ情報を保存する
            #       例: Image.objects.create(title=form.cleaned_data['title'], ...)
            # TODO: 実ファイル保存処理は今後追加する
            #       例: default_storage.save(filename, form.cleaned_data['file'])
            return render(request, 'accounts/image_upload.html', {
                'form': ImageUploadForm(),
                'channel_id': channel_id,
                'uploaded': True,  # 仮送信完了フラグ
            })
        return render(request, 'accounts/image_upload.html', {
            'form': form,
            'channel_id': channel_id,
            'uploaded': False,
        })


class AudioUploadView(View):
    """
    音声アップロード画面。

    今回はUI・遷移の骨組みのみ。送信後は「仮送信完了」メッセージを同画面に表示する。
    TODO: DB完成後に form.cleaned_data を使って音声メタ情報を保存する
    TODO: 実ファイル保存処理（storage への書き込み）を追加する
    TODO: channel_id や user と紐づける処理を追加する
    """

    def get(self, request, channel_id: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        form = AudioUploadForm()
        return render(request, 'accounts/audio_upload.html', {
            'form': form,
            'channel_id': channel_id,
            'uploaded': False,
        })

    def post(self, request, channel_id: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        form = AudioUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # TODO: DB完成後に音声メタ情報を保存する
            #       例: Audio.objects.create(title=form.cleaned_data['title'], ...)
            # TODO: 実ファイル保存処理は今後追加する
            #       例: default_storage.save(filename, form.cleaned_data['file'])
            return render(request, 'accounts/audio_upload.html', {
                'form': AudioUploadForm(),
                'channel_id': channel_id,
                'uploaded': True,  # 仮送信完了フラグ
            })
        return render(request, 'accounts/audio_upload.html', {
            'form': form,
            'channel_id': channel_id,
            'uploaded': False,
        })
