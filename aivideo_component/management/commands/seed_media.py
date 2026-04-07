"""
開発用メディアシーダー。

alice / bob / admin の 3 ユーザーに対して以下を生成する:
  - UserGoogleAccount  (Google アカウントのダミー)
  - OauthToken         (暗号化済みダミートークン)
  - YoutubeChannel     (YouTube チャンネルのダミー)
  - GeneratedImage × 3 (1×1 PNG ダミー画像)
  - GeneratedAudio × 3 (0.1 秒 WAV ダミー音声)

実行:
    python manage.py seed_media

冪等: 既存レコードはスキップする（重複しない）。
ファイル: media/seed/images/ と media/seed/audios/ に保存する。
"""
import io
import os
import struct
import wave
import zlib
from datetime import timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone


# ─────────────────────────────────────────────────────────────
# シードデータ定義
# ─────────────────────────────────────────────────────────────

USERS_SEED = [
    {
        "email": "alice@example.com",
        "google_sub": "mock_sub_alice_001",
        "google_email": "alice.google@example.com",
        "name": "Alice",
        "channel_id": "UCAlice0000000000000001",
        "channel_title": "Alice's Channel",
        "channel_handle": "@alice_channel",
        "images": [
            {"title": "Alice 都市背景",  "color": (100, 149, 237), "aspect": "16:9", "w": 1920, "h": 1080},
            {"title": "Alice 自然風景",  "color": (34, 139, 34),  "aspect": "16:9", "w": 1920, "h": 1080},
            {"title": "Alice ポートレート", "color": (255, 182, 193), "aspect": "9:16", "w": 1080, "h": 1920},
        ],
        "audios": [
            {"title": "Alice BGM 明るい",     "duration": 30.0, "codec": "wav"},
            {"title": "Alice BGM 落ち着く",   "duration": 60.0, "codec": "wav"},
            {"title": "Alice ナレーション用",  "duration": 10.0, "codec": "wav"},
        ],
    },
    {
        "email": "bob@example.com",
        "google_sub": "mock_sub_bob_002",
        "google_email": "bob.google@example.com",
        "name": "Bob",
        "channel_id": "UCBob00000000000000001",
        "channel_title": "Bob's Tech Channel",
        "channel_handle": "@bob_tech",
        "images": [
            {"title": "Bob オフィス背景", "color": (70, 130, 180),  "aspect": "16:9", "w": 1920, "h": 1080},
            {"title": "Bob テック系",    "color": (0, 191, 255),   "aspect": "16:9", "w": 1920, "h": 1080},
            {"title": "Bob 夜景",        "color": (25, 25, 112),   "aspect": "16:9", "w": 1920, "h": 1080},
        ],
        "audios": [
            {"title": "Bob BGM クール",          "duration": 45.0, "codec": "wav"},
            {"title": "Bob BGM エネルギッシュ",   "duration": 90.0, "codec": "wav"},
            {"title": "Bob 効果音",               "duration": 5.0,  "codec": "wav"},
        ],
    },
    {
        "email": "admin@example.com",
        "google_sub": "mock_sub_admin_003",
        "google_email": "admin.google@example.com",
        "name": "Admin",
        "channel_id": "UCAdmin000000000000001",
        "channel_title": "Admin Test Channel",
        "channel_handle": "@admin_test",
        "images": [
            {"title": "Admin テスト画像 A", "color": (220, 20, 60),  "aspect": "16:9", "w": 1920, "h": 1080},
            {"title": "Admin テスト画像 B", "color": (255, 165, 0),  "aspect": "1:1",  "w": 1080, "h": 1080},
            {"title": "Admin テスト画像 C", "color": (148, 0, 211),  "aspect": "9:16", "w": 1080, "h": 1920},
        ],
        "audios": [
            {"title": "Admin テスト音声 A", "duration": 15.0, "codec": "wav"},
            {"title": "Admin テスト音声 B", "duration": 30.0, "codec": "wav"},
            {"title": "Admin テスト音声 C", "duration": 60.0, "codec": "wav"},
        ],
    },
]


# ─────────────────────────────────────────────────────────────
# ダミーファイル生成ヘルパー
# ─────────────────────────────────────────────────────────────

def _make_png(r: int, g: int, b: int) -> bytes:
    """指定色の 1×1 PNG を返す。"""
    def chunk(ctype: bytes, data: bytes) -> bytes:
        c = zlib.crc32(ctype + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + ctype + data + struct.pack(">I", c)

    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = b"\x00" + bytes([r, g, b])
    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")
    return b"\x89PNG\r\n\x1a\n" + ihdr + idat + iend


def _make_wav(duration_sec: float, sample_rate: int = 44100) -> bytes:
    """指定時間の無音 WAV を返す。"""
    buf = io.BytesIO()
    n_frames = int(sample_rate * duration_sec)
    with wave.open(buf, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\x00\x00" * n_frames)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────
# コマンド
# ─────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Seed GeneratedImage / GeneratedAudio for 3 development users"

    def handle(self, *args, **kwargs):
        from accounts.models import User
        from aivideo_component.models import GeneratedAudio, GeneratedImage
        from google_auth.models import OauthToken, UserGoogleAccount, YoutubeChannel
        from google_auth.services import encrypt_token

        self.stdout.write("─" * 60)
        self.stdout.write("🌱 seed_media start")
        self.stdout.write("─" * 60)

        for seed in USERS_SEED:
            self.stdout.write(f"\n▶ {seed['email']}")

            # ── User ──────────────────────────────────────────────────
            try:
                user = User.objects.get(email=seed["email"])
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"  skip: user not found ({seed['email']}) — run seed_users first"
                    )
                )
                continue

            # ── UserGoogleAccount ─────────────────────────────────────
            google_account, created = UserGoogleAccount.objects.get_or_create(
                google_sub=seed["google_sub"],
                defaults={
                    "user": user,
                    "email": seed["google_email"],
                    "name": seed["name"],
                    "account_status": "active",
                },
            )
            self._log(created, "UserGoogleAccount", seed["google_sub"])

            # ── OauthToken ────────────────────────────────────────────
            dummy_access = f"dummy_access_token_{seed['name'].lower()}"
            dummy_refresh = f"dummy_refresh_token_{seed['name'].lower()}"
            _, created = OauthToken.objects.get_or_create(
                user_google_account=google_account,
                defaults={
                    "access_token_encrypted": encrypt_token(dummy_access),
                    "refresh_token_encrypted": encrypt_token(dummy_refresh),
                    "token_type": "Bearer",
                    "expires_at": timezone.now() + timedelta(hours=1),
                },
            )
            self._log(created, "OauthToken", seed["google_email"])

            # ── YoutubeChannel ────────────────────────────────────────
            channel, created = YoutubeChannel.objects.get_or_create(
                youtube_channel_id=seed["channel_id"],
                defaults={
                    "user_google_account": google_account,
                    "title": seed["channel_title"],
                    "handle": seed["channel_handle"],
                    "is_default": True,
                    "is_active": True,
                },
            )
            self._log(created, "YoutubeChannel", seed["channel_title"])

            # ── GeneratedImage × 3 ───────────────────────────────────
            for img_seed in seed["images"]:
                if GeneratedImage.objects.filter(
                    youtube_channel=channel, title=img_seed["title"]
                ).exists():
                    self.stdout.write(f"    [Image] skip:    {img_seed['title']}")
                    continue

                png_data = _make_png(*img_seed["color"])
                safe_name = img_seed["title"].replace(" ", "_").replace("/", "_")
                filename = f"seed_{seed['name'].lower()}_{safe_name}.png"

                image = GeneratedImage(
                    youtube_channel=channel,
                    title=img_seed["title"],
                    original_filename=filename,
                    mime_type="image/png",
                    file_size_bytes=len(png_data),
                    width=img_seed["w"],
                    height=img_seed["h"],
                    aspect_ratio=img_seed["aspect"],
                    validation_status="valid",
                )
                image.image_file.save(filename, ContentFile(png_data), save=True)
                self.stdout.write(
                    self.style.SUCCESS(f"    [Image] created: {img_seed['title']}")
                )

            # ── GeneratedAudio × 3 ───────────────────────────────────
            for aud_seed in seed["audios"]:
                if GeneratedAudio.objects.filter(
                    youtube_channel=channel, title=aud_seed["title"]
                ).exists():
                    self.stdout.write(f"    [Audio] skip:    {aud_seed['title']}")
                    continue

                wav_data = _make_wav(aud_seed["duration"])
                safe_name = aud_seed["title"].replace(" ", "_").replace("/", "_")
                filename = f"seed_{seed['name'].lower()}_{safe_name}.wav"

                audio = GeneratedAudio(
                    youtube_channel=channel,
                    title=aud_seed["title"],
                    original_filename=filename,
                    mime_type="audio/wav",
                    file_size_bytes=len(wav_data),
                    duration_sec=aud_seed["duration"],
                    sample_rate=44100,
                    channels=1,
                    codec=aud_seed["codec"],
                    validation_status="valid",
                )
                audio.audio_file.save(filename, ContentFile(wav_data), save=True)
                self.stdout.write(
                    self.style.SUCCESS(f"    [Audio] created: {aud_seed['title']}")
                )

        self.stdout.write("\n" + "─" * 60)
        self.stdout.write(self.style.SUCCESS("✅ seed_media complete"))

    def _log(self, created: bool, label: str, name: str) -> None:
        if created:
            self.stdout.write(self.style.SUCCESS(f"  [{label}] created: {name}"))
        else:
            self.stdout.write(f"  [{label}] skip:    {name}")
