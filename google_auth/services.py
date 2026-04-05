"""
Google OAuth / YouTube Data API サービス層

GOOGLE_OAUTH_MOCK=True の場合はすべてモックデータで動作し、
実際の Google API への通信は行わない。
"""

import base64
import hashlib
import json
import urllib.parse
import urllib.request

from cryptography.fernet import Fernet
from django.conf import settings

# ─── OAuth 定数 ───────────────────────────────────────────────────────────────

GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'
YOUTUBE_CHANNELS_URL = 'https://www.googleapis.com/youtube/v3/channels'

SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/youtube',
]


# ─── トークン暗号化 ───────────────────────────────────────────────────────────

def _fernet() -> Fernet:
    """SECRET_KEY から Fernet キーを導出する"""
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_token(token: str) -> str:
    return _fernet().encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    return _fernet().decrypt(encrypted.encode()).decode()


# ─── Mock データ ──────────────────────────────────────────────────────────────

def mock_exchange_code(code: str) -> dict:
    return {
        'access_token': 'mock_access_token_xyz789',
        'refresh_token': 'mock_refresh_token_abc123',
        'token_type': 'Bearer',
        'scope': ' '.join(SCOPES),
        'expires_in': 3600,
    }


def mock_fetch_userinfo(email: str) -> dict:
    return {
        'sub': f'mock_google_sub_{email.split("@")[0]}',
        'email': email,
        'name': email.split('@')[0].capitalize(),
        'picture': '',
    }


def mock_fetch_channels() -> list:
    return [
        {
            'id': 'UCmockChannel001',
            'snippet': {
                'title': 'Mock YouTube Channel',
                'customUrl': '@mockchannel',
                'thumbnails': {
                    'default': {'url': ''},
                },
            },
        },
    ]


# ─── 実 API 実装 ──────────────────────────────────────────────────────────────

def build_auth_url(state: str) -> str:
    params = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': settings.GOOGLE_REDIRECT_URI,
        'response_type': 'code',
        'scope': ' '.join(SCOPES),
        'access_type': 'offline',
        'prompt': 'consent',
        'state': state,
    }
    return GOOGLE_AUTH_URL + '?' + urllib.parse.urlencode(params)


def exchange_code_for_tokens(code: str) -> dict:
    data = urllib.parse.urlencode({
        'code': code,
        'client_id': settings.GOOGLE_CLIENT_ID,
        'client_secret': settings.GOOGLE_CLIENT_SECRET,
        'redirect_uri': settings.GOOGLE_REDIRECT_URI,
        'grant_type': 'authorization_code',
    }).encode()
    req = urllib.request.Request(GOOGLE_TOKEN_URL, data=data, method='POST')
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_google_userinfo(access_token: str) -> dict:
    req = urllib.request.Request(
        GOOGLE_USERINFO_URL,
        headers={'Authorization': f'Bearer {access_token}'},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_youtube_channels(access_token: str) -> list:
    url = YOUTUBE_CHANNELS_URL + '?' + urllib.parse.urlencode({
        'part': 'snippet',
        'mine': 'true',
        'maxResults': 50,
    })
    req = urllib.request.Request(
        url,
        headers={'Authorization': f'Bearer {access_token}'},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        return data.get('items', [])
