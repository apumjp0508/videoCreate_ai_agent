"""
ThumbnailGeneration Activity のインターフェース定義。

Workflow はここだけを参照する。実装（dummy / 本番）は一切知らない。

責務:
  動画の要約・タイトルをもとに外部 AI（画像生成 AI など）へリクエストを送り、
  サムネイル画像を生成してその URL を返す。
  YouTube 固有の知識を持たず、どのプラットフォームにも転用できる抽象レベルに留める。

ルール:
  - 各 Activity は専用の Input / Output dataclass を持つ
  - Activity スタブ関数は raise NotImplementedError のみ
  - 実装ファイルは @activity.defn(name="<同じ名前>") で同一名を登録すること
  - フィールド追加は末尾に default 付きで追加する（後方互換）

Activity 一覧:
  1. generate_thumbnail  ─ 動画要約・タイトルをもとにサムネイル画像を生成
"""
from __future__ import annotations

from dataclasses import dataclass, field

from temporalio import activity


# ─────────────────────────────────────────────────────────────
# 1. generate_thumbnail  ─ サムネイル生成
# ─────────────────────────────────────────────────────────────

@dataclass
class GenerateThumbnailInput:
    """
    外部 AI にサムネイルを生成させるための入力。

    video_url      : 動画ファイルの URL（代表フレーム抽出に使う実装もある）
    title          : generate_video_metadata が生成したタイトル
    video_summary  : analyze_video_content が生成した動画要約
    style          : サムネイルのスタイルヒント（実装依存）
    language       : テキスト要素の言語（デフォルト: 日本語）
    """
    job_id: str
    video_url: str
    title: str
    video_summary: str
    style: str = "auto"
    language: str = "ja"


@dataclass
class GenerateThumbnailOutput:
    """
    外部 AI が生成したサムネイル画像の情報。
    プラットフォーム非依存の汎用形式で返す。

    thumbnail_url  : 生成されたサムネイル画像の URL（空文字の場合はスキップ）
    """
    thumbnail_url: str
    # TODO: 本実装では画像サイズ・フォーマットなどのメタデータを追加する
    metadata: dict = field(default_factory=dict)


@activity.defn
async def generate_thumbnail(
    input: GenerateThumbnailInput,
) -> GenerateThumbnailOutput:
    raise NotImplementedError
