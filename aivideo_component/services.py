"""
アップロードファイルのメタ情報抽出と provider 適合判定。

責務の分担:
  extract_image_meta / extract_audio_meta
      アップロードファイルオブジェクトを受け取り、メタ情報 dict を返す。
      戻り値は GeneratedImage / GeneratedAudio の create / update にそのまま渡せる。

  validate_image / validate_audio
      保存済みモデルインスタンスを受け取り、
      validation_status / validation_message を判定して DB を更新する。

依存ライブラリ:
  Pillow  - 画像の width / height 取得 (pip install Pillow)
  mutagen - 音声の duration / sample_rate 等取得 (pip install mutagen)
  どちらも未インストール時はメタ不完全のまま動作継続する。
"""

from __future__ import annotations

import mimetypes
from decimal import ROUND_HALF_UP, Decimal
from math import gcd
from typing import Optional


# ─────────────────────── メタ情報抽出 ───────────────────────


def extract_image_meta(uploaded_file) -> dict:
    """
    InMemoryUploadedFile / TemporaryUploadedFile から画像メタ情報を抽出する。

    戻り値 dict のキーは GeneratedImage のフィールド名と一致しており、
    GeneratedImage.objects.create(**meta, ...) にそのまま展開できる。

    Pillow が未インストールの場合は width / height / aspect_ratio を省略する
    （モデル側のデフォルト値 None / '' が入る）。
    """
    original_filename: str = getattr(uploaded_file, 'name', '') or ''
    file_size_bytes: int = getattr(uploaded_file, 'size', 0)

    # Content-Type ヘッダ優先、なければ拡張子から推測
    mime_type: str = getattr(uploaded_file, 'content_type', '') or ''
    if not mime_type and original_filename:
        guessed, _ = mimetypes.guess_type(original_filename)
        mime_type = guessed or ''

    width: Optional[int] = None
    height: Optional[int] = None
    aspect_ratio: str = ''

    try:
        from PIL import Image as PilImage  # type: ignore[import]

        uploaded_file.seek(0)
        with PilImage.open(uploaded_file) as img:
            width, height = img.size
            aspect_ratio = _reduce_aspect(width, height)
        uploaded_file.seek(0)
    except ImportError:
        pass  # pip install Pillow で有効になる
    except Exception:
        pass  # 不正ファイル等の解析失敗は無視してアップロード続行

    return {
        'original_filename': original_filename,
        'mime_type': mime_type,
        'file_size_bytes': file_size_bytes,
        'width': width,
        'height': height,
        'aspect_ratio': aspect_ratio,
    }


def extract_audio_meta(uploaded_file) -> dict:
    """
    InMemoryUploadedFile / TemporaryUploadedFile から音声メタ情報を抽出する。

    戻り値 dict のキーは GeneratedAudio のフィールド名と一致しており、
    GeneratedAudio.objects.create(**meta, ...) にそのまま展開できる。

    mutagen が未インストールの場合は duration_sec 等を None で返す。
    """
    original_filename: str = getattr(uploaded_file, 'name', '') or ''
    file_size_bytes: int = getattr(uploaded_file, 'size', 0)

    mime_type: str = getattr(uploaded_file, 'content_type', '') or ''
    if not mime_type and original_filename:
        guessed, _ = mimetypes.guess_type(original_filename)
        mime_type = guessed or ''

    duration_sec: Optional[Decimal] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    codec: str = ''

    try:
        import mutagen  # type: ignore[import]

        uploaded_file.seek(0)
        audio_info = mutagen.File(uploaded_file)
        if audio_info is not None and hasattr(audio_info, 'info'):
            info = audio_info.info
            raw_duration = getattr(info, 'length', None)
            if raw_duration is not None:
                # DecimalField(max_digits=10, decimal_places=3) に合わせて変換
                duration_sec = Decimal(str(float(raw_duration))).quantize(
                    Decimal('0.001'), rounding=ROUND_HALF_UP
                )
            sample_rate = getattr(info, 'sample_rate', None)
            channels = getattr(info, 'channels', None)
            # MP3Info → 'mp3', VorbisInfo → 'vorbis' など
            codec = type(info).__name__.lower().replace('info', '')
        uploaded_file.seek(0)
    except ImportError:
        pass  # pip install mutagen で有効になる
    except Exception:
        pass  # 解析失敗は無視してアップロード続行

    return {
        'original_filename': original_filename,
        'mime_type': mime_type,
        'file_size_bytes': file_size_bytes,
        'duration_sec': duration_sec,
        'sample_rate': sample_rate,
        'channels': channels,
        'codec': codec,
    }


# ─────────────────────── Provider 適合判定 ───────────────────────


def validate_image(image) -> None:
    """
    GeneratedImage インスタンスの validation_status / validation_message を
    Runway / Pika / Kling の仕様と照合して更新し、DB に保存する。

    validation_message の例:
      "Runway: 使用可\nPika: 要確認（アスペクト比 4:3 は非推奨）\nKling: 不可（非対応フォーマット）"

    provider 仕様の定数は本モジュール上部の _RUNWAY_* / _PIKA_* / _KLING_* を参照。
    """
    status, message = _check_image_providers(image)
    # update() で auto_now の updated_at を避けつつ直接 DB 更新
    type(image).objects.filter(pk=image.pk).update(
        validation_status=status,
        validation_message=message,
    )
    # インスタンスのキャッシュも一致させる
    image.validation_status = status
    image.validation_message = message


def validate_audio(audio) -> None:
    """
    GeneratedAudio インスタンスの validation_status / validation_message を
    provider 適合判定に基づいて更新し、DB に保存する。
    """
    status, message = _check_audio_providers(audio)
    type(audio).objects.filter(pk=audio.pk).update(
        validation_status=status,
        validation_message=message,
    )
    audio.validation_status = status
    audio.validation_message = message


# ─────────────────────── Provider 仕様定数 ───────────────────────
# 各 provider の公式ドキュメントを確認して必要に応じて更新してください。

# --- Runway Gen-3 Alpha ---
_RUNWAY_IMAGE_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
_RUNWAY_IMAGE_MIN_SIDE = 512          # px
_RUNWAY_IMAGE_MAX_SIDE = 4096         # px
_RUNWAY_IMAGE_MAX_BYTES = 10 * 1024 * 1024   # 10 MB
_RUNWAY_AUDIO_MIME_TYPES = {'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/x-wav'}
_RUNWAY_AUDIO_MAX_DURATION_SEC = 95   # 秒（Gen-3 最大生成尺に合わせた目安）

# --- Pika 2.x ---
_PIKA_IMAGE_MIME_TYPES = {'image/jpeg', 'image/png'}
_PIKA_IMAGE_MIN_SIDE = 360            # px
_PIKA_IMAGE_MAX_BYTES = 50 * 1024 * 1024     # 50 MB
_PIKA_AUDIO_MIME_TYPES = {'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/x-wav', 'audio/aac'}
_PIKA_AUDIO_MAX_DURATION_SEC = 180    # 秒

# --- Kling AI ---
_KLING_IMAGE_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
_KLING_IMAGE_MIN_SIDE = 300           # px
_KLING_IMAGE_MAX_SIDE = 4096          # px
_KLING_IMAGE_MAX_BYTES = 10 * 1024 * 1024    # 10 MB
_KLING_IMAGE_PREFERRED_ASPECTS = {'16:9', '9:16', '1:1'}
_KLING_AUDIO_MIME_TYPES = {'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/x-wav'}
_KLING_AUDIO_MAX_DURATION_SEC = 180   # 秒


# ─────────────────────── 内部: 判定ロジック ───────────────────────


def _check_image_providers(image) -> tuple[str, str]:
    """
    各 provider の仕様定数と画像メタ情報を照合し、
    (validation_status, validation_message) を返す。

    validation_message の形式（1 provider 1 行）:
      "Runway: 使用可"
      "Pika: 要確認（ファイルサイズが大きい）"
      "Kling: 不可（非対応フォーマット）"

    overall status:
      'valid'   … すべての provider で問題なし
      'invalid' … 1 つ以上の provider で不可
      ※ '要確認' のみの場合も 'invalid' として扱い、目視確認を促す
    """
    lines = []
    has_invalid = False

    # ── Runway ──
    runway_issues = _image_issues(
        image,
        allowed_mime=_RUNWAY_IMAGE_MIME_TYPES,
        min_side=_RUNWAY_IMAGE_MIN_SIDE,
        max_side=_RUNWAY_IMAGE_MAX_SIDE,
        max_bytes=_RUNWAY_IMAGE_MAX_BYTES,
    )
    if runway_issues:
        has_invalid = True
        lines.append(f"Runway: 不可（{'／'.join(runway_issues)}）")
    else:
        lines.append('Runway: 使用可')

    # ── Pika ──
    pika_issues = _image_issues(
        image,
        allowed_mime=_PIKA_IMAGE_MIME_TYPES,
        min_side=_PIKA_IMAGE_MIN_SIDE,
        max_side=None,
        max_bytes=_PIKA_IMAGE_MAX_BYTES,
    )
    if pika_issues:
        has_invalid = True
        lines.append(f"Pika: 不可（{'／'.join(pika_issues)}）")
    else:
        # Pika はアスペクト比が非標準でも動作することが多いため「要確認」扱い
        if image.aspect_ratio and image.aspect_ratio not in ('16:9', '9:16', '1:1'):
            has_invalid = True
            lines.append(f'Pika: 要確認（アスペクト比 {image.aspect_ratio} は非推奨）')
        else:
            lines.append('Pika: 使用可')

    # ── Kling ──
    kling_issues = _image_issues(
        image,
        allowed_mime=_KLING_IMAGE_MIME_TYPES,
        min_side=_KLING_IMAGE_MIN_SIDE,
        max_side=_KLING_IMAGE_MAX_SIDE,
        max_bytes=_KLING_IMAGE_MAX_BYTES,
    )
    if image.aspect_ratio and image.aspect_ratio not in _KLING_IMAGE_PREFERRED_ASPECTS:
        kling_issues.append(f'アスペクト比 {image.aspect_ratio} は非推奨（推奨: 16:9 / 9:16 / 1:1）')
    if kling_issues:
        has_invalid = True
        lines.append(f"Kling: 不可（{'／'.join(kling_issues)}）")
    else:
        lines.append('Kling: 使用可')

    status = 'invalid' if has_invalid else 'valid'
    return status, '\n'.join(lines)


def _check_audio_providers(audio) -> tuple[str, str]:
    """
    各 provider の仕様定数と音声メタ情報を照合し、
    (validation_status, validation_message) を返す。
    """
    lines = []
    has_invalid = False

    # ── Runway ──
    runway_issues = _audio_issues(
        audio,
        allowed_mime=_RUNWAY_AUDIO_MIME_TYPES,
        max_duration=_RUNWAY_AUDIO_MAX_DURATION_SEC,
    )
    if runway_issues:
        has_invalid = True
        lines.append(f"Runway: 不可（{'／'.join(runway_issues)}）")
    else:
        lines.append('Runway: 使用可')

    # ── Pika ──
    pika_issues = _audio_issues(
        audio,
        allowed_mime=_PIKA_AUDIO_MIME_TYPES,
        max_duration=_PIKA_AUDIO_MAX_DURATION_SEC,
    )
    if pika_issues:
        has_invalid = True
        lines.append(f"Pika: 不可（{'／'.join(pika_issues)}）")
    else:
        lines.append('Pika: 使用可')

    # ── Kling ──
    kling_issues = _audio_issues(
        audio,
        allowed_mime=_KLING_AUDIO_MIME_TYPES,
        max_duration=_KLING_AUDIO_MAX_DURATION_SEC,
    )
    if kling_issues:
        has_invalid = True
        lines.append(f"Kling: 不可（{'／'.join(kling_issues)}）")
    else:
        lines.append('Kling: 使用可')

    status = 'invalid' if has_invalid else 'valid'
    return status, '\n'.join(lines)


# ─────────────────────── 内部: チェックヘルパー ───────────────────────


def _image_issues(image, allowed_mime, min_side, max_side, max_bytes) -> list[str]:
    """指定された制約に対してひっかかる問題点を文字列リストで返す。"""
    issues = []

    if image.mime_type and image.mime_type not in allowed_mime:
        issues.append(f'非対応フォーマット（{image.mime_type}）')

    if image.file_size_bytes and max_bytes and image.file_size_bytes > max_bytes:
        mb = image.file_size_bytes / (1024 * 1024)
        issues.append(f'ファイルサイズ超過（{mb:.1f}MB）')

    if image.width and image.height:
        short = min(image.width, image.height)
        long = max(image.width, image.height)
        if min_side and short < min_side:
            issues.append(f'解像度不足（短辺 {short}px、最小 {min_side}px）')
        if max_side and long > max_side:
            issues.append(f'解像度超過（長辺 {long}px、最大 {max_side}px）')

    return issues


def _audio_issues(audio, allowed_mime, max_duration) -> list[str]:
    """指定された制約に対してひっかかる問題点を文字列リストで返す。"""
    issues = []

    if audio.mime_type and audio.mime_type not in allowed_mime:
        issues.append(f'非対応フォーマット（{audio.mime_type}）')

    if audio.duration_sec is not None and max_duration:
        if float(audio.duration_sec) > max_duration:
            issues.append(f'尺が長すぎる（{float(audio.duration_sec):.1f}秒、上限 {max_duration}秒）')

    return issues


# ─────────────────────── 内部ユーティリティ ───────────────────────


def _reduce_aspect(width: int, height: int) -> str:
    """GCD で簡約したアスペクト比文字列を返す。例: (1920, 1080) → '16:9'"""
    g = gcd(width, height)
    return f"{width // g}:{height // g}"
