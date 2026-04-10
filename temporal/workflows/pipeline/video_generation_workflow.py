"""
VideoGenerationWorkflow  ─ 動画生成を担う子 Workflow。

責務:
  - 素材・AI設定・リクエスト定義の取得
  - AI リクエストの組み立てと送信
  - 生成完了まで状況をポーリング
  - 完成動画 URL を返す

この Workflow は「動画を生成して URL を返す」だけに集中する。
YouTube への投稿は YoutubePublishWorkflow が担う。

入力:  VideoGenerationWorkflowInput  (temporal/pipeline_types.py)
出力:  VideoGenerationWorkflowOutput (temporal/pipeline_types.py)
"""
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from temporal.activities.job_progress.interfaces import (
        UpdateJobProgressInput,
        update_job_progress,
    )
    from temporal.activities.video_generation.interfaces import (
        BuildAiRequestInput,
        FetchAiConfigInput,
        FetchGeneratedVideoInput,
        FetchMaterialsInput,
        FetchRequestDefinitionInput,
        PollGenerationStatusInput,
        SaveGeneratedVideoInput,
        SubmitAiRequestInput,
        build_ai_request,
        fetch_ai_config,
        fetch_generated_video,
        fetch_materials,
        fetch_request_definition,
        poll_generation_status,
        save_generated_video,
        submit_ai_request,
    )
    from temporal.pipeline_types import (
        VideoGenerationWorkflowInput,
        VideoGenerationWorkflowOutput,
    )

# 生成状況ポーリングの最大試行回数
_MAX_POLL_ATTEMPTS = 60
# ポーリング間隔
_POLL_INTERVAL = timedelta(seconds=10)


@workflow.defn
class VideoGenerationWorkflow:
    """
    動画生成子 Workflow。

    Activity の呼び出し順:
      1. fetch_materials          ─ 素材取得
      2. fetch_ai_config          ─ AI設定取得
      3. fetch_request_definition ─ リクエスト定義取得
      4. build_ai_request         ─ AIリクエスト生成
      5. submit_ai_request        ─ AIへ送信
      6. poll_generation_status   ─ 生成完了まで繰り返し
      7. fetch_generated_video    ─ 完成動画取得
    """

    @workflow.run
    async def run(self, input: VideoGenerationWorkflowInput) -> VideoGenerationWorkflowOutput:
        workflow.logger.info(
            "VideoGenerationWorkflow started  job_id=%s  user_id=%s",
            input.job_id, input.user_id,
        )

        # ── Step 1: 素材取得 ──────────────────────────────────────
        materials = await workflow.execute_activity(
            fetch_materials,
            FetchMaterialsInput(
                job_id=input.job_id,
                user_id=input.user_id,
                image_ids=input.image_ids,
                audio_ids=input.audio_ids,
            ),
            start_to_close_timeout=timedelta(minutes=2),
        )
        workflow.logger.info("fetch_materials done  job_id=%s", input.job_id)

        # ── Step 2: AI設定取得 ─────────────────────────────────────
        ai_config = await workflow.execute_activity(
            fetch_ai_config,
            FetchAiConfigInput(
                job_id=input.job_id,
                credential_id=input.credential_id,
                model_id=input.model_id,
            ),
            start_to_close_timeout=timedelta(minutes=2),
        )
        workflow.logger.info("fetch_ai_config done  job_id=%s  model=%s", input.job_id, ai_config.model_name)

        # ── Step 3: リクエスト定義取得 ─────────────────────────────
        request_def = await workflow.execute_activity(
            fetch_request_definition,
            FetchRequestDefinitionInput(
                job_id=input.job_id,
                prompt_id=input.prompt_id,
            ),
            start_to_close_timeout=timedelta(minutes=2),
        )
        workflow.logger.info("fetch_request_definition done  job_id=%s", input.job_id)

        # ── Step 4: AIリクエスト生成 ───────────────────────────────
        ai_request = await workflow.execute_activity(
            build_ai_request,
            BuildAiRequestInput(
                job_id=input.job_id,
                model_name=ai_config.model_name,
                api_endpoint=ai_config.api_endpoint,
                prompt_text=request_def.prompt_text,
                image_ids=materials.image_ids,
                audio_ids=materials.audio_ids,
                config_params=ai_config.params,
                format_settings=request_def.format_settings,
                video_length_sec=input.video_length,
                images=materials.images,
                audios=materials.audios,
            ),
            start_to_close_timeout=timedelta(minutes=2),
        )
        workflow.logger.info("build_ai_request done  job_id=%s", input.job_id)

        # ── Step 5: AIへ送信 ───────────────────────────────────────
        # 進捗更新: AI呼び出し開始
        await workflow.execute_activity(
            update_job_progress,
            UpdateJobProgressInput(
                job_id=input.job_id,
                step="CALL_AI",
                event_type="AI_REQUEST_SENT",
                message="AI動画生成リクエストを送信します",
            ),
            start_to_close_timeout=timedelta(minutes=1),
        )
        submit_result = await workflow.execute_activity(
            submit_ai_request,
            SubmitAiRequestInput(
                job_id=input.job_id,
                api_endpoint=ai_config.api_endpoint,
                credential_id=ai_config.credential_id,
                ai_request_payload=ai_request.ai_request_payload,
            ),
            start_to_close_timeout=timedelta(minutes=5),
        )
        workflow.logger.info(
            "submit_ai_request done  job_id=%s  generation_id=%s",
            input.job_id, submit_result.generation_id,
        )

        # ── Step 6: 生成完了まで状況確認（ポーリング） ────────────
        # 進捗更新: AI生成待機開始
        await workflow.execute_activity(
            update_job_progress,
            UpdateJobProgressInput(
                job_id=input.job_id,
                step="WAIT_AI_RESULT",
                event_type="STEP_UPDATED",
                message="AI動画の生成完了を待機しています",
                payload={"generation_id": submit_result.generation_id},
            ),
            start_to_close_timeout=timedelta(minutes=1),
        )
        poll_result = None
        for attempt in range(1, _MAX_POLL_ATTEMPTS + 1):
            poll_result = await workflow.execute_activity(
                poll_generation_status,
                PollGenerationStatusInput(
                    job_id=input.job_id,
                    generation_id=submit_result.generation_id,
                    credential_id=ai_config.credential_id,
                    api_endpoint=ai_config.api_endpoint,
                ),
                start_to_close_timeout=timedelta(minutes=1),
            )
            workflow.logger.info(
                "poll_generation_status  job_id=%s  attempt=%d  status=%s",
                input.job_id, attempt, poll_result.status,
            )

            if poll_result.is_failed:
                raise RuntimeError(
                    f"AI generation failed  job_id={input.job_id}  generation_id={submit_result.generation_id}"
                    + (f"  error={poll_result.error_message}" if poll_result.error_message else "")
                )

            if poll_result.is_complete:
                break

            # 完了していなければ待機してから再試行
            await workflow.sleep(_POLL_INTERVAL)
        else:
            raise TimeoutError(
                f"Generation polling timed out after {_MAX_POLL_ATTEMPTS} attempts  job_id={input.job_id}"
            )

        workflow.logger.info(
            "Generation completed  job_id=%s  video_url=%s",
            input.job_id, poll_result.video_url,
        )

        # 進捗更新: AI生成完了
        await workflow.execute_activity(
            update_job_progress,
            UpdateJobProgressInput(
                job_id=input.job_id,
                step="FETCH_VIDEO",
                event_type="AI_RENDER_COMPLETED",
                message="AI動画の生成が完了しました",
                payload={"generation_id": submit_result.generation_id},
                status="generated",
            ),
            start_to_close_timeout=timedelta(minutes=1),
        )

        # ── Step 7: 完成動画取得 ───────────────────────────────────
        video = await workflow.execute_activity(
            fetch_generated_video,
            FetchGeneratedVideoInput(
                job_id=input.job_id,
                generation_id=submit_result.generation_id,
                video_url=poll_result.video_url,
            ),
            start_to_close_timeout=timedelta(minutes=5),
        )
        workflow.logger.info(
            "fetch_generated_video done  job_id=%s  url=%s",
            input.job_id, video.video_url,
        )

        # ── Step 8: 完成動画を Django media に保存 ─────────────
        save_result = await workflow.execute_activity(
            save_generated_video,
            SaveGeneratedVideoInput(
                job_id=input.job_id,
                generation_id=submit_result.generation_id,
                video_url=video.video_url,
                video_metadata=video.video_metadata,
            ),
            start_to_close_timeout=timedelta(minutes=30),
        )
        workflow.logger.info(
            "save_generated_video done  job_id=%s  generated_video_id=%s  media_url=%s",
            input.job_id, save_result.generated_video_id, save_result.media_url,
        )

        return VideoGenerationWorkflowOutput(
            job_id=input.job_id,
            video_url=save_result.media_url,   # media URL を後続 Workflow に渡す
            generation_id=submit_result.generation_id,
        )
