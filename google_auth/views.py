import secrets
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from fetch_channel import get_client as get_fetch_channel_client
from fetch_channel.interfaces import ChannelInfo
from . import services
from .models import OauthToken, UserGoogleAccount, YoutubeChannel


def _save_channels(channels: list[ChannelInfo], google_account: UserGoogleAccount, user) -> int:
    """取得したチャンネル一覧をすべてDBに保存する。保存件数を返す。"""
    already_has_default = YoutubeChannel.objects.filter(
        user_google_account__user=user,
        is_default=True,
    ).exists()

    saved = 0
    for i, channel_info in enumerate(channels):
        is_default = (not already_has_default) and (i == 0)
        YoutubeChannel.objects.update_or_create(
            youtube_channel_id=channel_info.id,
            defaults={
                'user_google_account': google_account,
                'title': channel_info.title,
                'handle': channel_info.handle,
                'thumbnail_url': channel_info.thumbnail_url,
                'description': channel_info.description,
                'country': channel_info.country,
                'uploads_playlist_id': channel_info.uploads_playlist_id,
                'subscriber_count': channel_info.subscriber_count,
                'video_count': channel_info.video_count,
                'view_count': channel_info.view_count,
                'is_default': is_default,
                'is_active': True,
                'fetched_at': datetime.now(timezone.utc),
            },
        )
        saved += 1
    return saved


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
        next_url = request.GET.get('next', '')
        if next_url:
            request.session['oauth_next'] = next_url

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
            # ── 1. トークン・ユーザー情報の取得 ──────────────────────────────
            if settings.GOOGLE_OAUTH_MOCK:
                token_data = services.mock_exchange_code(code)
                userinfo = services.mock_fetch_userinfo(request.user.email)
            else:
                token_data = services.exchange_code_for_tokens(code)
                userinfo = services.fetch_google_userinfo(token_data['access_token'])

            access_token = token_data['access_token']

            # チャンネル取得は fetch_channel クライアントに委譲（mock / 本番を隠蔽）
            channel_client = get_fetch_channel_client(mock=settings.GOOGLE_OAUTH_MOCK)
            channels: list[ChannelInfo] = channel_client.fetch(access_token)

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

            # ── 4. チャンネルをすべてDBに自動保存 ────────────────────────────
            _save_channels(channels, google_account, request.user)

        except Exception as e:
            messages.error(request, f'連携中にエラーが発生しました: {e}')
            if not request.user.is_active:
                return redirect('accounts:register_connect_google')
            return redirect('google_auth:channel_list')

        # 登録フロー中（is_active=False）なら有効化して通常バックエンドで再ログイン
        if not request.user.is_active:
            request.user.is_active = True
            request.user.save(update_fields=['is_active'])
            from django.contrib.auth import login as auth_login
            auth_login(request, request.user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('accounts:dashboard')

        next_url = request.session.pop('oauth_next', None)
        messages.success(request, 'Googleアカウントを連携しました。')
        if next_url:
            return redirect(next_url)
        return redirect('google_auth:channel_list')


class SyncChannelsView(LoginRequiredMixin, View):
    """
    既存の OauthToken を使って YouTube チャンネルを再取得・同期する。

    OAuth 認証なしで fetch_channel クライアントを直接呼び出す。
    Google アカウントが未連携の場合は OAuth フローへフォールバック。
    """
    login_url = '/login/'

    def get(self, request):
        next_url = request.GET.get('next', '')

        google_accounts = list(
            UserGoogleAccount.objects
            .filter(user=request.user)
            .prefetch_related('oauth_token')
        )

        if not google_accounts:
            # Google アカウント未連携 → OAuth フローへ
            if next_url:
                request.session['oauth_next'] = next_url
            return redirect('google_auth:oauth_start')

        channel_client = get_fetch_channel_client(mock=settings.GOOGLE_OAUTH_MOCK)
        total_saved = 0
        errors = []

        for account in google_accounts:
            try:
                token_obj = account.oauth_token
                access_token = services.decrypt_token(token_obj.access_token_encrypted)
                channels: list[ChannelInfo] = channel_client.fetch(access_token)
                total_saved += _save_channels(channels, account, request.user)
            except Exception as e:
                errors.append(str(e))

        if errors:
            messages.error(request, f'チャンネル取得中にエラーが発生しました: {errors[0]}')
        else:
            messages.success(request, f'チャンネル情報を同期しました（{total_saved}件）。')

        if next_url:
            return redirect(next_url)
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
