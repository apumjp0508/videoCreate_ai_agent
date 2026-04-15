"""
VideoGeneration Activity の Django / 純粋ロジック実装。

実装済み Activity:
  - fetch_materials          Django ORM（GeneratedImage / GeneratedAudio）
  - fetch_ai_config          Django ORM（UserVideoAiCredential / VideoAiModel / VideoAiProvider）
  - fetch_request_definition Django ORM（Prompt）
  - build_ai_request         純粋ロジック（外部依存なし）
  - save_generated_video     httpx でダウンロード → Django media に保存 → GeneratedVideo 作成

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
    SaveGeneratedVideoInput,
    SaveGeneratedVideoOutput,
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
        self._attach_descriptions(input.job_id, images, audios)
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

    def _attach_descriptions(
        self,
        job_id_str: str,
        images: list[ImageMaterial],
        audios: list[AudioMaterial],
    ) -> None:
        """VideoJobAsset からこのJobでの素材説明を取得して ImageMaterial / AudioMaterial に付与する。"""
        from jobs.models import VideoJobAsset
        try:
            job_id = int(job_id_str)
        except (ValueError, TypeError):
            return
        asset_desc_map = {
            a.asset_id: a.description
            for a in VideoJobAsset.objects.filter(job_id=job_id)
        }
        for img in images:
            img.description = asset_desc_map.get(img.id, "")
        for aud in audios:
            aud.description = asset_desc_map.get(aud.id, "")

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

    # ── save_generated_video（ダウンロード + media 保存）─────────

    async def save_generated_video(
        self, input: SaveGeneratedVideoInput
    ) -> SaveGeneratedVideoOutput:
        """
        AI プロバイダーの動画 URL からダウンロードして Django media に保存する。

        処理フロー:
          1. httpx で動画をストリーミングダウンロード
          2. Django FileField 経由で media/generated_videos/ に保存
          3. GeneratedVideo レコードを DB 作成
          4. VideoJob.generated_video を更新
          5. 絶対 media URL を返す（YoutubePublishWorkflow が動画アップロードに使用）
        """
        logger.info(
            "save_generated_video  job_id=%s  gen_id=%s  url=%s",
            input.job_id, input.generation_id, input.video_url,
        )

        video_bytes, content_type = await self._stream_download(input.video_url)
        result = await sync_to_async(self._persist_to_media)(
            input, video_bytes, content_type
        )

        logger.info(
            "save_generated_video done  job_id=%s  generated_video_id=%d  size=%d bytes  url=%s",
            input.job_id, result.generated_video_id, len(video_bytes), result.media_url,
        )
        return result

    @staticmethod
    async def _stream_download(url: str) -> tuple[bytes, str]:
        """httpx で URL からバイト列と Content-Type を取得する。"""
        import httpx

        logger.info("Downloading video: %s", url)
        async with httpx.AsyncClient(follow_redirects=True, timeout=600.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "video/mp4")
            data = response.content
        logger.info("Download complete: %d bytes  content_type=%s", len(data), content_type)
        return data, content_type

    @staticmethod
    def _persist_to_media(
        input: SaveGeneratedVideoInput,
        video_bytes: bytes,
        content_type: str,
    ) -> SaveGeneratedVideoOutput:
        """
        ダウンロードした動画を Django media ストレージに保存して
        GeneratedVideo / VideoJob を更新する（同期・DB トランザクション内）。
        """
        from django.conf import settings
        from django.core.files.base import ContentFile
        from jobs.models import GeneratedVideo, VideoJob

        # Content-Type からファイル拡張子を決定
        ext = _ext_from_content_type(content_type)
        filename = f"job{input.job_id}_gen{input.generation_id}.{ext}"

        meta = input.video_metadata or {}

        # GeneratedVideo レコードを作成して video_file を保存
        gv = GeneratedVideo(
            original_url=input.video_url[:1000],
            generation_id=input.generation_id,
            mime_type=content_type.split(";")[0].strip() or "video/mp4",
            file_size_bytes=len(video_bytes),
            duration_sec=meta.get("duration_sec"),
            resolution=meta.get("resolution", ""),
        )
        # FileField.save() がストレージへの書き込み + gv.save() を行う
        gv.video_file.save(filename, ContentFile(video_bytes), save=True)

        # VideoJob.generated_video を更新（generated_video_id カラムに書き込まれる）
        VideoJob.objects.filter(id=int(input.job_id)).update(generated_video=gv)

        # 絶対 URL を組み立てる
        base_url = getattr(settings, "SITE_BASE_URL", "http://localhost:8000").rstrip("/")
        media_url = f"{base_url}{gv.video_file.url}"

        return SaveGeneratedVideoOutput(
            generated_video_id=gv.id,
            media_url=media_url,
        )

    # ── build_ai_request（DB 駆動・プロバイダー別ビルダー）────────

    async def build_ai_request(
        self, input: BuildAiRequestInput
    ) -> BuildAiRequestOutput:
        """
        provider_key を元に DB からプロバイダー設定を取得し、
        対応するビルダーにプロバイダー固有のリクエストペイロードを組み立てさせる。

        provider_key は fetch_ai_config が返す config_params["provider_key"] から取得する。
        ビルダーの登録・ルーティングは request_builder/registry.py が担う。
        """
        logger.info(
            "build_ai_request  job_id=%s  model=%s",
            input.job_id, input.model_name,
        )

        provider_key = input.config_params.get("provider_key", "")
        if not provider_key:
            raise ValueError(
                f"build_ai_request: config_params に provider_key がありません  job_id={input.job_id}"
            )

        return await sync_to_async(self._build_sync)(input, provider_key)

    @staticmethod
    def _build_sync(input: BuildAiRequestInput, provider_key: str) -> BuildAiRequestOutput:
        """
        DB からプロバイダー設定を取得してビルダーを呼び出す（同期）。
        Django ORM を使うため sync_to_async でラップして呼ぶこと。
        """
        from temporal.activities.video_generation.request_builder.registry import (
            RequestBuilderNotFoundError,
            RequestConfigNotFoundError,
            get_builder,
        )

        try:
            builder, config = get_builder(provider_key)
        except RequestBuilderNotFoundError as exc:
            raise ValueError(str(exc)) from exc
        except RequestConfigNotFoundError as exc:
            raise ValueError(str(exc)) from exc

        logger.info(
            "_build_sync  job_id=%s  provider=%s  builder=%s",
            input.job_id, provider_key, type(builder).__name__,
        )
        return builder.build(input, config)


# ─────────────────────────────────────────────────────────────
# LocalVideoGenerationService  ─ ローカル開発用サービス
# ─────────────────────────────────────────────────────────────

class LocalVideoGenerationService(DjangoVideoGenerationService):
    """
    ローカル開発環境用の VideoGeneration サービス。

    外部 AI API（submit / poll / fetch_generated）はダミーのまま使い、
    save_generated_video だけ本番実装を使う。ただし HTTP ダウンロードは
    スキップし、プレースホルダーファイルを media に保存する。

    これにより APP_ENV=local でも:
      - GeneratedVideo レコードが DB に作成される
      - VideoJob.generated_video が正しく紐づく
      - 後続の YoutubePublishWorkflow がダミー URL を受け取れる
    """

    async def save_generated_video(
        self, input: SaveGeneratedVideoInput
    ) -> SaveGeneratedVideoOutput:
        logger.info(
            "[Local] save_generated_video  job_id=%s  gen_id=%s  url=%s",
            input.job_id, input.generation_id, input.video_url,
        )
        result = await sync_to_async(self._persist_placeholder)(input)
        logger.info(
            "[Local] save_generated_video done  job_id=%s  generated_video_id=%d",
            input.job_id, result.generated_video_id,
        )
        return result

    @staticmethod
    def _persist_placeholder(input: SaveGeneratedVideoInput) -> SaveGeneratedVideoOutput:
        """
        HTTP ダウンロードをスキップして空のプレースホルダーファイルを保存する。
        original_url にダミー URL を記録しておき、media_url はダミー URL をそのまま返す。
        """
        from django.core.files.base import ContentFile
        from jobs.models import GeneratedVideo, VideoJob

        meta = input.video_metadata or {}
        filename = f"job{input.job_id}_gen{input.generation_id}_placeholder.mp4"

        gv = GeneratedVideo(
            original_url=input.video_url[:1000],
            generation_id=input.generation_id,
            mime_type="video/mp4",
            file_size_bytes=0,
            duration_sec=meta.get("duration_sec"),
            resolution=meta.get("resolution", ""),
        )
        # 空ファイルをプレースホルダーとして保存
        gv.video_file.save(filename, ContentFile(b""), save=True)

        VideoJob.objects.filter(id=int(input.job_id)).update(generated_video=gv)

        # ダミー URL をそのまま media_url として返す（後続ダミー処理が受け取る）
        return SaveGeneratedVideoOutput(
            generated_video_id=gv.id,
            media_url=input.video_url,
        )


# ─────────────────────────────────────────────────────────────
# モジュールレベルユーティリティ
# ─────────────────────────────────────────────────────────────

def _ext_from_content_type(content_type: str) -> str:
    """Content-Type ヘッダから動画ファイルの拡張子を返す。"""
    ct = content_type.lower().split(";")[0].strip()
    return {
        "video/mp4":       "mp4",
        "video/webm":      "webm",
        "video/quicktime": "mov",
        "video/x-msvideo": "avi",
        "video/x-matroska":"mkv",
    }.get(ct, "mp4")
