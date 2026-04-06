import uuid

from django.core.management.base import BaseCommand

from temporal.types import VideoJobInput
from video_ai.services import start_video_job


class Command(BaseCommand):
    help = "Temporal の VideoJobWorkflow をテスト実行する"

    def add_arguments(self, parser):
        parser.add_argument("--user-id",           type=int, default=1)
        parser.add_argument("--video-ai-config-id", type=int, default=1)
        parser.add_argument("--prompt-id",          type=int, default=1)
        parser.add_argument("--oauth-record-id",    type=int, default=0)
        parser.add_argument("--youtube-channel-id", type=str, default="")
        parser.add_argument("--publish-mode",       type=str, default="private",
                            choices=["private", "unlisted", "public"])

    def handle(self, *args, **options):
        input = VideoJobInput(
            job_id=str(uuid.uuid4()),
            request_id=str(uuid.uuid4()),
            user_id=options["user_id"],
            video_ai_config_id=options["video_ai_config_id"],
            prompt_id=options["prompt_id"],
            oauth_record_id=options["oauth_record_id"],
            youtube_channel_id=options["youtube_channel_id"],
            publish_mode=options["publish_mode"],
        )

        self.stdout.write(f"🚀 Workflow 起動中...")
        self.stdout.write(f"   job_id:            {input.job_id}")
        self.stdout.write(f"   user_id:           {input.user_id}")
        self.stdout.write(f"   video_ai_config_id:{input.video_ai_config_id}")
        self.stdout.write(f"   prompt_id:         {input.prompt_id}")
        self.stdout.write(f"   publish_mode:      {input.publish_mode}")

        result = start_video_job(input)

        self.stdout.write(self.style.SUCCESS("✅ Workflow 完了"))
        self.stdout.write(f"   job_id:           {result.job_id}")
        self.stdout.write(f"   youtube_video_id: {result.youtube_video_id}")
        self.stdout.write(f"   youtube_video_url:{result.youtube_video_url}")
