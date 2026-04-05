# =============================================================================
# accounts/dummy_data.py
#
# channel選択画面が未完成のため、仮データをここに集約している。
# DB完成後は、このファイルの各関数の中身をDB取得処理に置き換えるだけでよい。
# =============================================================================

# -----------------------------------------------------------------------------
# チャンネルの仮データ
# TODO: DB完成後は Channel モデルから取得する
#       例: Channel.objects.get(pk=channel_id)
# -----------------------------------------------------------------------------
DUMMY_CHANNELS = {
    1: 'Channel A',
    2: 'Channel B',
    3: 'Channel C',
}

# -----------------------------------------------------------------------------
# チャンネルごとの画像候補（仮データ）
# TODO: DB完成後は Image.objects.filter(channel_id=channel_id) に置き換える
# -----------------------------------------------------------------------------
DUMMY_IMAGE_CHOICES = {
    1: [
        ('image_1_a', '背景画像 1-A（都市）'),
        ('image_1_b', '背景画像 1-B（自然）'),
    ],
    2: [
        ('image_2_a', '背景画像 2-A（オフィス）'),
        ('image_2_b', '背景画像 2-B（海）'),
    ],
    3: [
        ('image_3_a', '背景画像 3-A（夜景）'),
        ('image_3_b', '背景画像 3-B（空）'),
    ],
}

# -----------------------------------------------------------------------------
# チャンネルごとの音声候補（仮データ）
# TODO: DB完成後は Audio.objects.filter(channel_id=channel_id) に置き換える
# -----------------------------------------------------------------------------
DUMMY_AUDIO_CHOICES = {
    1: [
        ('audio_1_a', 'BGM 1-A（明るい）'),
        ('audio_1_b', 'BGM 1-B（落ち着く）'),
    ],
    2: [
        ('audio_2_a', 'BGM 2-A（クール）'),
        ('audio_2_b', 'BGM 2-B（エネルギッシュ）'),
    ],
    3: [
        ('audio_3_a', 'BGM 3-A（ドラマチック）'),
        ('audio_3_b', 'BGM 3-B（やさしい）'),
    ],
}


def get_channel_name(channel_id: int) -> str:
    """
    channel_id に対応するチャンネル名を返す。

    TODO: DB完成後はこの関数の中身を以下のように置き換える
          from .models import Channel
          return Channel.objects.get(pk=channel_id).name
    """
    return DUMMY_CHANNELS.get(channel_id, f'Channel {channel_id}')


def get_image_choices(channel_id: int) -> list:
    """
    channel_id に応じた画像の選択肢を返す。
    choices は [(value, label), ...] の形式。

    TODO: DB完成後はこの関数の中身を以下のように置き換える
          from .models import Image
          qs = Image.objects.filter(channel_id=channel_id)
          return [(img.pk, img.name) for img in qs]
    """
    return DUMMY_IMAGE_CHOICES.get(channel_id, [('', '（画像候補なし）')])


def get_audio_choices(channel_id: int) -> list:
    """
    channel_id に応じた音声の選択肢を返す。
    choices は [(value, label), ...] の形式。

    TODO: DB完成後はこの関数の中身を以下のように置き換える
          from .models import Audio
          qs = Audio.objects.filter(channel_id=channel_id)
          return [(audio.pk, audio.name) for audio in qs]
    """
    return DUMMY_AUDIO_CHOICES.get(channel_id, [('', '（音声候補なし）')])
