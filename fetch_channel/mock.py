"""
FetchChannelClient のモック実装。

GOOGLE_OAUTH_MOCK=True の環境で使用する。
実際の YouTube Data API には接続せず、固定データを返す。
"""
import logging

from fetch_channel.interfaces import ChannelInfo

logger = logging.getLogger(__name__)


class MockFetchChannelClient:
    """固定チャンネルデータを返すモッククライアント。"""

    def fetch(self, token: str) -> list[ChannelInfo]:
        logger.info('[MockFetchChannelClient] fetch called (token ignored)')
        return [
            ChannelInfo(
                id='UCmockChannel001',
                title='Mock YouTube Channel',
                handle='@mockchannel',
                thumbnail_url='',
            ),
        ]
