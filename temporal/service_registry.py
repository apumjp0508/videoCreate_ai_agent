"""
環境変数 APP_ENV に基づいて各 Activity のサービス実装を選択・注入する。

    APP_ENV=local   → ダミーサービス（外部API呼び出しなし・ローカル開発用）
    APP_ENV=staging → 本サービス（実際のAPI・外部連携あり）

使い方（worker_pipeline.py から呼ぶだけ）:
    from temporal.service_registry import configure_services
    configure_services()

新しい Activity グループを追加する方法:
    1. _build_registry() 内に ActivityGroupConfig を1ブロック追加する
    2. services dict に APP_ENV_LOCAL / APP_ENV_STAGING それぞれのファクトリーを書く
    3. それ以外のファイルは変更不要
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ─────────────────────── 環境定数 ───────────────────────

APP_ENV_LOCAL   = "local"
APP_ENV_STAGING = "staging"

_VALID_ENVS: frozenset[str] = frozenset({APP_ENV_LOCAL, APP_ENV_STAGING})


def _resolve_env() -> str:
    """
    APP_ENV 環境変数を読んで検証済みの環境名を返す。
    未設定の場合は "local" をデフォルトとする。

    Raises:
        ValueError: APP_ENV が有効な値以外のとき
    """
    raw = os.environ.get("APP_ENV", APP_ENV_LOCAL).strip().lower()
    if raw not in _VALID_ENVS:
        raise ValueError(
            f"APP_ENV='{raw}' は無効です。"
            f"有効な値: {sorted(_VALID_ENVS)}"
        )
    return raw


# ─────────────────────── レジストリ定義 ───────────────────────

@dataclass
class ActivityGroupConfig:
    """
    1つの Activity グループ（例: video_generation）の設定。

    Attributes:
        name:         ログ表示用のグループ名
        dummy_module: _service を書き換える対象モジュール
        services:     { 環境名: サービスインスタンスを返すファクトリー }
    """
    name: str
    dummy_module: ModuleType
    services: dict[str, Callable[[], Any]]


def _build_registry() -> list[ActivityGroupConfig]:
    """
    各 Activity グループの設定リストを組み立てる。

    NOTE: Django 依存のサービスは django.setup() 後に import される必要があるため、
          この関数内で遅延インポートしている。
          configure_services() から呼ばれるため、呼び出し時点では必ず setup 済み。
    """
    # ── job_progress ──────────────────────────────────────────
    from temporal.activities.job_progress import dummy as jp_dummy
    from temporal.activities.job_progress.dummy import DummyJobProgressService
    from temporal.activities.job_progress.django_service import DjangoJobProgressService

    # ── video_generation ──────────────────────────────────────
    from temporal.activities.video_generation import dummy as vg_dummy
    from temporal.activities.video_generation.dummy import DummyVideoGenerationService
    from temporal.activities.video_generation.django_service import DjangoVideoGenerationService

    # ── video_metadata ────────────────────────────────────────
    from temporal.activities.video_metadata import dummy as vm_dummy
    from temporal.activities.video_metadata.dummy import DummyVideoMetadataService
    from temporal.activities.video_metadata.openai_service import OpenAIVideoMetadataService

    # ── thumbnail_generation ──────────────────────────────────
    from temporal.activities.thumbnail_generation import dummy as th_dummy
    from temporal.activities.thumbnail_generation.dummy import DummyThumbnailService
    from temporal.activities.thumbnail_generation.openai_service import OpenAIThumbnailService

    # ── youtube_publish ───────────────────────────────────────
    from temporal.activities.youtube_publish import dummy as yt_dummy
    from temporal.activities.youtube_publish.dummy import DummyYoutubePublishService
    from temporal.activities.youtube_publish.django_service import DjangoYoutubePublishService
    from temporal.activities.youtube_publish.youtube_api_service import YoutubeDataApiService

    return [
        ActivityGroupConfig(
            name="job_progress",
            dummy_module=jp_dummy,
            services={
                APP_ENV_LOCAL:   lambda: DummyJobProgressService(),
                APP_ENV_STAGING: lambda: DjangoJobProgressService(),
            },
        ),
        ActivityGroupConfig(
            name="video_generation",
            dummy_module=vg_dummy,
            services={
                APP_ENV_LOCAL:   lambda: DummyVideoGenerationService(),
                APP_ENV_STAGING: lambda: DjangoVideoGenerationService(),
            },
        ),
        ActivityGroupConfig(
            name="video_metadata",
            dummy_module=vm_dummy,
            services={
                APP_ENV_LOCAL:   lambda: DummyVideoMetadataService(),
                APP_ENV_STAGING: lambda: OpenAIVideoMetadataService(),
            },
        ),
        ActivityGroupConfig(
            name="thumbnail_generation",
            dummy_module=th_dummy,
            services={
                APP_ENV_LOCAL:   lambda: DummyThumbnailService(),
                APP_ENV_STAGING: lambda: OpenAIThumbnailService(),
            },
        ),
        ActivityGroupConfig(
            name="youtube_publish",
            dummy_module=yt_dummy,
            services={
                APP_ENV_LOCAL:   lambda: DummyYoutubePublishService(),
                APP_ENV_STAGING: lambda: DjangoYoutubePublishService(
                    youtube_api=YoutubeDataApiService()
                ),
            },
        ),
    ]


# ─────────────────────── 公開API ───────────────────────

def configure_services() -> str:
    """
    APP_ENV に応じて全 Activity グループの _service を一括で設定する。

    worker_pipeline.py の django.setup() 直後に一度だけ呼ぶこと。

    Returns:
        適用した環境名 ("local" | "staging")

    Raises:
        ValueError: APP_ENV が無効な値のとき
        KeyError:   いずれかのグループに env 対応のサービスが未登録のとき
    """
    env = _resolve_env()
    registry = _build_registry()

    logger.info("[service_registry] APP_ENV=%s  グループ数=%d", env, len(registry))

    for group in registry:
        factory = group.services.get(env)
        if factory is None:
            raise KeyError(
                f"'{group.name}' に env='{env}' のサービスが登録されていません。"
                f"登録済み: {list(group.services)}"
            )
        service = factory()
        group.dummy_module._service = service
        logger.info(
            "[service_registry]   %-25s → %s",
            group.name,
            type(service).__name__,
        )

    return env
