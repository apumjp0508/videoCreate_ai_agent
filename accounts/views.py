from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.views import View

from .forms import LoginForm, RegisterForm
from google_auth.models import YoutubeChannel


class RegisterView(View):
    def get(self, request):
        form = RegisterForm()
        return render(request, 'accounts/register.html', {'form': form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            # AllowAllUsersModelBackend を使い is_active=False でもセッションを維持する
            login(request, user, backend='django.contrib.auth.backends.AllowAllUsersModelBackend')
            return redirect('accounts:register_connect_google')
        return render(request, 'accounts/register.html', {'form': form})


class RegisterConnectGoogleView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('accounts:register')
        if request.user.is_active:
            return redirect('accounts:dashboard')
        return render(request, 'accounts/register_connect_google.html')


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
        if not request.user.is_active:
            return redirect('accounts:register_connect_google')
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
