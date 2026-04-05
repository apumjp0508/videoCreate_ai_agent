import secrets
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from . import services
from .models import OauthToken, UserGoogleAccount, YoutubeChannel


class ChannelListView(LoginRequiredMixin, View):
    login_url = '/login/'

    def get(self, request):
        google_accounts = (
            UserGoogleAccount.objects
            .filter(user=request.user)
            .prefetch_related('youtube_channels')
            .order_by('connected_at')
        )
        return render(request, 'google_auth/channel_list.html', {
            'google_accounts': google_accounts,
            'is_mock': settings.GOOGLE_OAUTH_MOCK,
        })


class GoogleOAuthStartView(LoginRequiredMixin, View):
    login_url = '/login/'

    def get(self, request):
        if settings.GOOGLE_OAUTH_MOCK:
            # モック: ステートは固定値でそのままコールバックへ
            return redirect('/auth/google/callback/?code=mock_code_12345&state=mock_state')

        state = secrets.token_urlsafe(16)
        request.session['google_oauth_state'] = state
        return redirect(services.build_auth_url(state))


class GoogleOAuthCallbackView(LoginRequiredMixin, View):
    login_url = '/login/'

    def get(self, request):
        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')

        if error:
            messages.error(request, f'Google認証がキャンセルされました: {error}')
            return redirect('google_auth:channel_list')

        if not code:
            messages.error(request, '認証コードが取得できませんでした。')
            return redirect('google_auth:channel_list')

        if not settings.GOOGLE_OAUTH_MOCK:
            saved_state = request.session.pop('google_oauth_state', None)
            if state != saved_state:
                messages.error(request, 'セキュリティエラーが発生しました。もう一度お試しください。')
                return redirect('google_auth:channel_list')

        try:
            # ── 1. トークン・ユーザー情報・チャンネル情報の取得 ──────────────
            if settings.GOOGLE_OAUTH_MOCK:
                token_data = services.mock_exchange_code(code)
                userinfo = services.mock_fetch_userinfo(request.user.email)
                raw_channels = services.mock_fetch_channels()
            else:
                token_data = services.exchange_code_for_tokens(code)
                userinfo = services.fetch_google_userinfo(token_data['access_token'])
                raw_channels = services.fetch_youtube_channels(token_data['access_token'])

            access_token = token_data['access_token']
            refresh_token = token_data.get('refresh_token', '')
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=token_data.get('expires_in', 3600)
            )

            # ── 2. UserGoogleAccount の保存/更新 ─────────────────────────────
            google_account, _ = UserGoogleAccount.objects.update_or_create(
                google_sub=userinfo['sub'],
                defaults={
                    'user': request.user,
                    'email': userinfo['email'],
                    'name': userinfo.get('name', ''),
                    'picture_url': userinfo.get('picture', ''),
                    'account_status': UserGoogleAccount.ACCOUNT_STATUS_ACTIVE,
                    'last_synced_at': datetime.now(timezone.utc),
                    'disconnected_at': None,
                },
            )

            # ── 3. OauthToken の保存/更新 ─────────────────────────────────────
            OauthToken.objects.update_or_create(
                user_google_account=google_account,
                defaults={
                    'access_token_encrypted': services.encrypt_token(access_token),
                    'refresh_token_encrypted': (
                        services.encrypt_token(refresh_token) if refresh_token else ''
                    ),
                    'token_type': token_data.get('token_type', 'Bearer'),
                    'scope': token_data.get('scope', ''),
                    'expires_at': expires_at,
                    'last_refreshed_at': datetime.now(timezone.utc),
                    'revoked_at': None,
                },
            )

            # ── 4. YouTubeチャンネルの保存/更新 ──────────────────────────────
            now = datetime.now(timezone.utc)
            already_has_default = YoutubeChannel.objects.filter(
                user_google_account=google_account,
                is_default=True,
            ).exists()

            for i, ch in enumerate(raw_channels):
                snippet = ch.get('snippet', {})
                thumbnails = snippet.get('thumbnails', {})
                thumbnail_url = (
                    thumbnails.get('default', {}).get('url', '')
                    or thumbnails.get('medium', {}).get('url', '')
                )
                YoutubeChannel.objects.update_or_create(
                    youtube_channel_id=ch['id'],
                    defaults={
                        'user_google_account': google_account,
                        'title': snippet.get('title', ''),
                        'handle': snippet.get('customUrl', ''),
                        'thumbnail_url': thumbnail_url,
                        'is_default': not already_has_default and i == 0,
                        'is_active': True,
                        'fetched_at': now,
                    },
                )

            channel_count = len(raw_channels)
            messages.success(
                request,
                f'{google_account.email} の連携が完了しました。'
                f'チャンネル {channel_count} 件を取得しました。',
            )

        except Exception as e:
            messages.error(request, f'連携中にエラーが発生しました: {e}')

        return redirect('google_auth:channel_list')


class YoutubeSelectView(LoginRequiredMixin, View):
    """
    YouTube選択画面。

    ログイン中ユーザーが持つYouTubeチャンネル一覧を表示し、
    1つ選択したら content_select へ遷移する。
    channel_id は YoutubeChannel の DB主キー（整数）を使う。
    """
    login_url = '/login/'

    def get(self, request):
        channels = (
            YoutubeChannel.objects
            .filter(user_google_account__user=request.user, is_active=True)
            .select_related('user_google_account')
            .order_by('-is_default', 'title')
        )
        return render(request, 'google_auth/youtube_select.html', {
            'channels': channels,
        })


class ChannelSetDefaultView(LoginRequiredMixin, View):
    login_url = '/login/'

    def post(self, request, channel_id):
        channel = YoutubeChannel.objects.filter(
            id=channel_id,
            user_google_account__user=request.user,
        ).first()
        if not channel:
            messages.error(request, 'チャンネルが見つかりません。')
            return redirect('google_auth:channel_list')

        # 同じ Google アカウント配下のデフォルトを解除してから設定
        YoutubeChannel.objects.filter(
            user_google_account=channel.user_google_account
        ).update(is_default=False)
        channel.is_default = True
        channel.save(update_fields=['is_default'])

        messages.success(request, f'「{channel.title}」をデフォルトチャンネルに設定しました。')
        return redirect('google_auth:channel_list')
