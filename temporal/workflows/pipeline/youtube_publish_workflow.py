"""
YoutubePublishWorkflow  ─ YouTube 投稿を担う子 Workflow。

責務:
  - OAuth トークンの取得・更新
  - 投稿設定の取得
  - アップロードリクエストの組み立てと実行
  - サムネイル設定（thumbnail_url がある場合のみ）
  - 公開設定の反映
  - 投稿結果の保存

この Workflow は「動画 URL を受け取り YouTube へ投稿して結果を返す」だけに集中する。
動画の生成は VideoGenerationWorkflow が担う。

入力:  YoutubePublishWorkflowInput  (temporal/pipeline_types.py)
出力:  YoutubePublishWorkflowOutput (temporal/pipeline_types.py)
"""
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from temporal.activities.job_progress.interfaces import (
        UpdateJobProgressInput,
        update_job_progress,
    )
    from temporal.activities.video_generation.interfaces import (
        FetchRequestDefinitionInput,
        fetch_request_definition,
    )
    from temporal.activities.video_metadata.interfaces import (
        AnalyzeVideoContentInput,
        GenerateVideoMetadataInput,
        analyze_video_content,
        generate_video_metadata,
    )
    from temporal.activities.thumbnail_generation.interfaces import (
        GenerateThumbnailInput,
        generate_thumbnail,
    )
    from temporal.activities.youtube_publish.interfaces import (
        ApplyPublishSettingsInput,
        BuildUploadRequestInput,
        FetchOAuthTokenInput,
        FetchPublishSettingsInput,
        FetchYoutubeAccountInput,
        RefreshAccessTokenInput,
        SavePublishResultInput,
        SetThumbnailInput,
        UploadVideoToYoutubeInput,
        apply_publish_settings,
        build_upload_request,
        fetch_oauth_token,
        fetch_publish_settings,
        fetch_youtube_account,
        refresh_access_token,
        save_publish_result,
        set_thumbnail,
        upload_video_to_youtube,
    )
    from temporal.pipeline_types import (
        YoutubePublishWorkflowInput,
        YoutubePublishWorkflowOutput,
    )


@workflow.defn
class YoutubePublishWorkflow:
    """
    YouTube 投稿子 Workflow。

    Activity の呼び出し順:
      1.  fetch_youtube_account   ─ YouTubeアカウント情報取得
      2.  fetch_oauth_token       ─ OAuthトークン取得
      3.  refresh_access_token    ─ 期限切れなら更新（条件付き）
      4a. fetch_request_definition ─ プロンプトテキスト取得
      4b. analyze_video_content   ─ 動画を外部AIに送信して要約取得
      4c. generate_video_metadata ─ 要約+プロンプトからタイトル/説明/タグ生成
      4d. generate_thumbnail      ─ 要約+タイトルからサムネイル画像生成
      4.  fetch_publish_settings  ─ 投稿設定取得（AI生成メタ情報でオーバーライド）
      5.  build_upload_request    ─ アップロード要求データ作成
      6.  upload_video_to_youtube ─ YouTube動画アップロード実行
      7.  set_thumbnail           ─ サムネイル設定（生成された thumbnail_url がある場合のみ）
      8.  apply_publish_settings  ─ 公開設定反映（任意）
      9.  save_publish_result     ─ 投稿結果保存
    """

    @workflow.run
    async def run(self, input: YoutubePublishWorkflowInput) -> YoutubePublishWorkflowOutput:
        workflow.logger.info(
            "YoutubePublishWorkflow started  job_id=%s  channel=%s",
            input.job_id, input.youtube_channel_id,
        )

        # ── Step 1: YouTubeアカウント情報取得 ──────────────────────
        account = await workflow.execute_activity(
            fetch_youtube_account,
            FetchYoutubeAccountInput(
                job_id=input.job_id,
                user_id=input.user_id,
                youtube_channel_id=input.youtube_channel_id,
            ),
            start_to_close_timeout=timedelta(minutes=2),
        )
        workflow.logger.info("fetch_youtube_account done  job_id=%s", input.job_id)

        # ── Step 2: OAuthトークン取得 ──────────────────────────────
        token = await workflow.execute_activity(
            fetch_oauth_token,
            FetchOAuthTokenInput(
                job_id=input.job_id,
                oauth_record_id=input.oauth_record_id,
            ),
            start_to_close_timeout=timedelta(minutes=2),
        )
        workflow.logger.info("fetch_oauth_token done  job_id=%s  expired=%s", input.job_id, token.is_expired)

        # ── Step 3: アクセストークン更新（期限切れの場合のみ） ──────
        access_token = token.access_token
        if token.is_expired:
            refreshed = await workflow.execute_activity(
                refresh_access_token,
                RefreshAccessTokenInput(
                    job_id=input.job_id,
                    oauth_record_id=input.oauth_record_id,
                    refresh_token=token.refresh_token,
                ),
                start_to_close_timeout=timedelta(minutes=2),
            )
            access_token = refreshed.access_token
            workflow.logger.info("refresh_access_token done  job_id=%s", input.job_id)

        # ── Step 4a: プロンプトテキスト取得 ───────────────────────
        request_def = await workflow.execute_activity(
            fetch_request_definition,
            FetchRequestDefinitionInput(
                job_id=input.job_id,
                prompt_id=input.prompt_id,
            ),
            start_to_close_timeout=timedelta(minutes=2),
        )
        workflow.logger.info("fetch_request_definition done  job_id=%s  prompt_id=%s", input.job_id, input.prompt_id)

        # ── Step 4b: 動画コンテンツ解析（外部 AI） ────────────────
        video_analysis = await workflow.execute_activity(
            analyze_video_content,
            AnalyzeVideoContentInput(
                job_id=input.job_id,
                video_url=input.video_url,
            ),
            start_to_close_timeout=timedelta(minutes=10),
        )
        workflow.logger.info("analyze_video_content done  job_id=%s", input.job_id)

        # ── Step 4c: 動画メタ情報生成（外部 AI） ──────────────────
        video_metadata = await workflow.execute_activity(
            generate_video_metadata,
            GenerateVideoMetadataInput(
                job_id=input.job_id,
                video_summary=video_analysis.summary,
                prompt_text=request_def.prompt_text,
            ),
            start_to_close_timeout=timedelta(minutes=5),
        )
        workflow.logger.info(
            "generate_video_metadata done  job_id=%s  title=%s",
            input.job_id, video_metadata.title,
        )

        # ── Step 4d: サムネイル生成（外部 AI） ────────────────────
        thumbnail_result = await workflow.execute_activity(
            generate_thumbnail,
            GenerateThumbnailInput(
                job_id=input.job_id,
                video_url=input.video_url,
                title=video_metadata.title,
                video_summary=video_analysis.summary,
            ),
            start_to_close_timeout=timedelta(minutes=10),
        )
        workflow.logger.info(
            "generate_thumbnail done  job_id=%s  thumbnail_url=%s",
            input.job_id, thumbnail_result.thumbnail_url,
        )

        # ── Step 4: 投稿設定取得（AI 生成メタ情報をオーバーライドとして渡す） ──
        publish_settings = await workflow.execute_activity(
            fetch_publish_settings,
            FetchPublishSettingsInput(
                job_id=input.job_id,
                user_id=input.user_id,
                title_override=video_metadata.title,
                description_override=video_metadata.description,
                tags_override=video_metadata.tags,
                publish_mode_override=input.publish_mode,
            ),
            start_to_close_timeout=timedelta(minutes=2),
        )
        workflow.logger.info("fetch_publish_settings done  job_id=%s", input.job_id)

        # ── Step 5: アップロード要求データ作成 ────────────────────
        upload_req = await workflow.execute_activity(
            build_upload_request,
            BuildUploadRequestInput(
                job_id=input.job_id,
                video_url=input.video_url,
                channel_id=account.channel_id,
                title=publish_settings.title,
                description=publish_settings.description,
                tags=publish_settings.tags,
                category_id=publish_settings.category_id,
                publish_mode=publish_settings.publish_mode,
            ),
            start_to_close_timeout=timedelta(minutes=2),
        )
        workflow.logger.info("build_upload_request done  job_id=%s", input.job_id)

        # ── Step 6: YouTube動画アップロード実行 ────────────────────
        # 進捗更新: YouTubeアップロード開始（status を publishing に遷移）
        await workflow.execute_activity(
            update_job_progress,
            UpdateJobProgressInput(
                job_id=input.job_id,
                step="UPLOAD_YOUTUBE",
                event_type="YOUTUBE_UPLOAD_STARTED",
                message="YouTube へのアップロードを開始します",
                status="publishing",
            ),
            start_to_close_timeout=timedelta(minutes=1),
        )
        upload_result = await workflow.execute_activity(
            upload_video_to_youtube,
            UploadVideoToYoutubeInput(
                job_id=input.job_id,
                access_token=access_token,
                upload_request=upload_req.upload_request,
                video_url=upload_req.video_url,
            ),
            start_to_close_timeout=timedelta(minutes=30),
        )
        workflow.logger.info(
            "upload_video_to_youtube done  job_id=%s  yt_id=%s",
            input.job_id, upload_result.youtube_video_id,
        )

        # ── Step 7: サムネイル設定（generate_thumbnail で生成された URL がある場合のみ） ──
        if thumbnail_result.thumbnail_url:
            await workflow.execute_activity(
                set_thumbnail,
                SetThumbnailInput(
                    job_id=input.job_id,
                    youtube_video_id=upload_result.youtube_video_id,
                    access_token=access_token,
                    thumbnail_url=thumbnail_result.thumbnail_url,
                ),
                start_to_close_timeout=timedelta(minutes=5),
            )
            workflow.logger.info("set_thumbnail done  job_id=%s", input.job_id)

        # ── Step 8: 公開設定反映（任意） ───────────────────────────
        # NOTE: アップロード時に privacyStatus を設定済みだが、
        #       スケジュール公開など追加設定が必要な場合に使う
        await workflow.execute_activity(
            apply_publish_settings,
            ApplyPublishSettingsInput(
                job_id=input.job_id,
                youtube_video_id=upload_result.youtube_video_id,
                access_token=access_token,
                publish_mode=publish_settings.publish_mode,
            ),
            start_to_close_timeout=timedelta(minutes=5),
        )
        workflow.logger.info("apply_publish_settings done  job_id=%s", input.job_id)

        # ── Step 9: 投稿結果保存 ───────────────────────────────────
        await workflow.execute_activity(
            save_publish_result,
            SavePublishResultInput(
                job_id=input.job_id,
                youtube_video_id=upload_result.youtube_video_id,
                youtube_video_url=upload_result.youtube_video_url,
                publish_mode=publish_settings.publish_mode,
            ),
            start_to_close_timeout=timedelta(minutes=2),
        )
        workflow.logger.info("save_publish_result done  job_id=%s", input.job_id)

        return YoutubePublishWorkflowOutput(
            job_id=input.job_id,
            youtube_video_id=upload_result.youtube_video_id,
            youtube_video_url=upload_result.youtube_video_url,
        )
