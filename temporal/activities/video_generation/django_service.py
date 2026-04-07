"""
VideoGeneration Activity の Django / 純粋ロジック実装。

実装済み Activity:
  - fetch_materials          Django ORM（GeneratedImage / GeneratedAudio）
  - fetch_ai_config          Django ORM（UserVideoAiCredential / VideoAiModel / VideoAiProvider）
  - fetch_request_definition Django ORM（Prompt）
  - build_ai_request         純粋ロジック（外部依存なし）

AIプロバイダー固有 Activity は DummyVideoGenerationService を継承:
  - submit_ai_request        → 各プロバイダー実装に差し替える
  - poll_generation_status   → 各プロバイダー実装に差し替える
  - fetch_generated_video    → 各プロバイダー実装に差し替える

設計方針:
  - Activity は async def だが Django ORM は同期的 → sync_to_async でラップ
  - ユーザー所有権の検証はクエリに含め DB 側で保証する
  - API キーは Temporal ヒストリに含めない
    → credential_id を FetchAiConfigOutput に含め、submit_ai_request が DB から取得する

差し替え方:
  worker_pipeline.py で以下のように _service を上書きする:

    from temporal.activities.video_generation import dummy as vg_dummy
    from temporal.activities.video_generation.django_service import DjangoVideoGenerationService
    vg_dummy._service = DjangoVideoGenerationService()
"""
from __future__ import annotations

import logging

from asgiref.sync import sync_to_async

from temporal.activities.video_generation.dummy import DummyVideoGenerationService
from temporal.activities.video_generation.interfaces import (
    AudioMaterial,
    BuildAiRequestInput,
    BuildAiRequestOutput,
    FetchAiConfigInput,
    FetchAiConfigOutput,
    FetchMaterialsInput,
    FetchMaterialsOutput,
    FetchRequestDefinitionInput,
    FetchRequestDefinitionOutput,
    ImageMaterial,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# ドメイン例外
# ─────────────────────────────────────────────────────────────

class MaterialNotFoundError(Exception):
    """指定された素材が DB に存在しない、またはアクセス権がない場合。"""


class AiConfigNotFoundError(Exception):
    """Credential / Model が存在しない、無効、またはアクセス権がない場合。"""


class PromptNotFoundError(Exception):
    """指定された Prompt が DB に存在しない場合。"""


# ─────────────────────────────────────────────────────────────
# サービス実装
# ─────────────────────────────────────────────────────────────

class DjangoVideoGenerationService(DummyVideoGenerationService):
    """
    VideoGenerationServiceProtocol の具体実装。

    DB 操作・純粋ロジックのみ実装する。
    AIプロバイダー固有の処理（submit / poll / fetch_generated）は
    DummyVideoGenerationService を継承し、プロバイダーごとに差し替える。
    """

    # ── fetch_materials ─────────────────────────────────────────

    async def fetch_materials(
        self, input: FetchMaterialsInput
    ) -> FetchMaterialsOutput:
        logger.info(
            "fetch_materials  job_id=%s  user_id=%s  image_ids=%s  audio_ids=%s",
            input.job_id, input.user_id, input.image_ids, input.audio_ids,
        )
        return await sync_to_async(self._fetch_materials_sync)(input)

    def _fetch_materials_sync(self, input: FetchMaterialsInput) -> FetchMaterialsOutput:
        images = self._fetch_images(input.user_id, input.image_ids)
        audios = self._fetch_audios(input.user_id, input.audio_ids)
        return FetchMaterialsOutput(
            image_ids=[img.id for img in images],
            audio_ids=[aud.id for aud in audios],
            images=images,
            audios=audios,
        )

    def _fetch_images(self, user_id: int, image_ids: list[int]) -> list[ImageMaterial]:
        if not image_ids:
            return []
        from aivideo_component.models import GeneratedImage
        qs = GeneratedImage.objects.filter(
            id__in=image_ids,
            youtube_channel__user_google_account__user_id=user_id,
        ).select_related('youtube_channel')
        found = {obj.id: obj for obj in qs}
        missing = set(image_ids) - found.keys()
        if missing:
            raise MaterialNotFoundError(
                f"ImageMaterial not found or access denied: ids={sorted(missing)}"
            )
        return [self._to_image_material(found[id_]) for id_ in image_ids]

    def _fetch_audios(self, user_id: int, audio_ids: list[int]) -> list[AudioMaterial]:
        if not audio_ids:
            return []
        from aivideo_component.models import GeneratedAudio
        qs = GeneratedAudio.objects.filter(
            id__in=audio_ids,
            youtube_channel__user_google_account__user_id=user_id,
        ).select_related('youtube_channel')
        found = {obj.id: obj for obj in qs}
        missing = set(audio_ids) - found.keys()
        if missing:
            raise MaterialNotFoundError(
                f"AudioMaterial not found or access denied: ids={sorted(missing)}"
            )
        return [self._to_audio_material(found[id_]) for id_ in audio_ids]

    @staticmethod
    def _to_image_material(obj) -> ImageMaterial:
        return ImageMaterial(
            id=obj.id,
            title=obj.title,
            file_url=obj.image_file.url,
            mime_type=obj.mime_type or "",
            width=obj.width or 0,
            height=obj.height or 0,
            aspect_ratio=obj.aspect_ratio or "",
            file_size_bytes=obj.file_size_bytes or 0,
        )

    @staticmethod
    def _to_audio_material(obj) -> AudioMaterial:
        return AudioMaterial(
            id=obj.id,
            title=obj.title,
            file_url=obj.audio_file.url,
            mime_type=obj.mime_type or "",
            duration_sec=obj.duration_sec or 0.0,
            sample_rate=obj.sample_rate or 0,
            channels=obj.channels or 0,
            codec=obj.codec or "",
            file_size_bytes=obj.file_size_bytes or 0,
        )

    # ── fetch_ai_config ─────────────────────────────────────────

    async def fetch_ai_config(
        self, input: FetchAiConfigInput
    ) -> FetchAiConfigOutput:
        logger.info(
            "fetch_ai_config  job_id=%s  credential_id=%s  model_id=%s",
            input.job_id, input.credential_id, input.model_id,
        )
        return await sync_to_async(self._fetch_ai_config_sync)(input)

    def _fetch_ai_config_sync(self, input: FetchAiConfigInput) -> FetchAiConfigOutput:
        from video_ai.models import UserVideoAiCredential, VideoAiModel

        try:
            credential = (
                UserVideoAiCredential.objects
                .select_related('provider')
                .get(id=input.credential_id, is_active=True)
            )
        except UserVideoAiCredential.DoesNotExist:
            raise AiConfigNotFoundError(
                f"UserVideoAiCredential not found or inactive: id={input.credential_id}"
            )

        try:
            model = VideoAiModel.objects.get(
                id=input.model_id,
                provider=credential.provider,
                is_active=True,
            )
        except VideoAiModel.DoesNotExist:
            raise AiConfigNotFoundError(
                f"VideoAiModel not found or inactive: id={input.model_id} "
                f"provider={credential.provider.provider_key}"
            )

        return FetchAiConfigOutput(
            config_id=credential.id,
            credential_id=credential.id,   # submit_ai_request が API キー取得に使う
            model_name=model.model_name,
            api_endpoint=credential.provider.api_base_url,
            params={
                "provider_key": credential.provider.provider_key,
                "model_id": model.id,
            },
        )

    # ── fetch_request_definition ────────────────────────────────

    async def fetch_request_definition(
        self, input: FetchRequestDefinitionInput
    ) -> FetchRequestDefinitionOutput:
        logger.info(
            "fetch_request_definition  job_id=%s  prompt_id=%s",
            input.job_id, input.prompt_id,
        )
        return await sync_to_async(self._fetch_request_definition_sync)(input)

    def _fetch_request_definition_sync(
        self, input: FetchRequestDefinitionInput
    ) -> FetchRequestDefinitionOutput:
        from jobs.models import Prompt

        try:
            prompt = Prompt.objects.get(id=input.prompt_id)
        except Prompt.DoesNotExist:
            raise PromptNotFoundError(
                f"Prompt not found: id={input.prompt_id}"
            )

        return FetchRequestDefinitionOutput(
            prompt_id=prompt.id,
            prompt_text=prompt.prompt_text,
            format_settings={},  # 将来: プロンプトに紐づくフォーマット設定を追加
        )

    # ── build_ai_request（純粋ロジック）───────────────────────

    async def build_ai_request(
        self, input: BuildAiRequestInput
    ) -> BuildAiRequestOutput:
        """
        プロバイダー非依存の正規化ペイロードを組み立てる。

        各プロバイダー固有の submit_ai_request 実装がこのペイロードを
        プロバイダー API フォーマットに変換する。
        """
        logger.info(
            "build_ai_request  job_id=%s  model=%s",
            input.job_id, input.model_name,
        )
        payload = {
            # プロバイダー設定
            "model": input.model_name,
            "endpoint": input.api_endpoint,
            # コンテンツ
            "prompt": input.prompt_text,
            "image_urls": input.image_ids,   # 実装時は ids → URLs に変換済みを想定
            "audio_urls": input.audio_ids,   # 同上
            # フォーマット / パラメータ
            "format": input.format_settings,
            "params": input.config_params,
        }
        return BuildAiRequestOutput(ai_request_payload=payload)
