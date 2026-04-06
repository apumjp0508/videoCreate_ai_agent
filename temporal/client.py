"""
Temporal クライアントのファクトリ。
接続先は settings.TEMPORAL_HOST / TEMPORAL_NAMESPACE で変更可能。
"""
from django.conf import settings
from temporalio.client import Client


async def get_temporal_client() -> Client:
    return await Client.connect(
        settings.TEMPORAL_HOST,
        namespace=settings.TEMPORAL_NAMESPACE,
    )
