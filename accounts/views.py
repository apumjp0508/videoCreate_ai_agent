from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.views import View

from .forms import AudioUploadForm, ContentSelectForm, ImageUploadForm, LoginForm, RegisterForm
from .dummy_data import get_audio_choices, get_channel_name, get_image_choices


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


class ContentSelectView(View):
    """
    スクリプト / 画像 / 音声 を選択する画面（動画作成ステップ2）。

    URLパラメータ channel_id でどのチャンネル向けかを受け取る。
    現在はchannel選択画面が未完成のため、直接 /content/select/1/ のように
    アクセスして単体確認できる形にしている。

    TODO: channel選択画面が完成したら、そちらの送信先をこのURLに向けるだけでOK。
    """

    def get(self, request, channel_id: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        # チャンネル情報を取得（仮データ）
        # TODO: DB完成後は get_channel_name() 内部がDB取得に切り替わる
        channel_name = get_channel_name(channel_id)

        # チャンネルに応じた画像・音声の選択肢を取得（仮データ）
        # TODO: DB完成後は get_image_choices() / get_audio_choices() 内部が
        #       DB取得に切り替わる。このビューのコードは変更不要。
        image_choices = get_image_choices(channel_id)
        audio_choices = get_audio_choices(channel_id)

        form = ContentSelectForm(
            image_choices=image_choices,
            audio_choices=audio_choices,
        )

        context = {
            'form': form,
            'channel_id': channel_id,
            'channel_name': channel_name,
        }
        return render(request, 'accounts/content_select.html', context)

    def post(self, request, channel_id: int):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        channel_name = get_channel_name(channel_id)
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
            'channel_name': channel_name,
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
