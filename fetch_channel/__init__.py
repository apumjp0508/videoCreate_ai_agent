from fetch_channel.interfaces import ChannelInfo, FetchChannelClient
from fetch_channel.mock import MockFetchChannelClient
from fetch_channel.youtube_api import YouTubeApiFetchChannelClient


def get_client(*, mock: bool = False) -> FetchChannelClient:
    """
    FetchChannelClient を返すファクトリ。

    mock=True  → MockFetchChannelClient（固定データ）
    mock=False → YouTubeApiFetchChannelClient（YouTube Data API v3）
    """
    if mock:
        return MockFetchChannelClient()
    return YouTubeApiFetchChannelClient()


__all__ = [
    'ChannelInfo',
    'FetchChannelClient',
    'MockFetchChannelClient',
    'YouTubeApiFetchChannelClient',
    'get_client',
]
