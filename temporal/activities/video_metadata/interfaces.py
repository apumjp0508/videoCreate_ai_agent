"""
VideoMetadata Activity のインターフェース定義。

Workflow はここだけを参照する。実装（dummy / 本番）は一切知らない。

責務:
  動画コンテンツを外部 AI に送信して動画メタ情報（タイトル・説明・タグ・カテゴリ）を
  自動生成するための Activity 契約を定義する。
  YouTube 固有の知識を持たず、どのプラットフォームにも転用できる抽象レベルに留める。

ルール:
  - 各 Activity は専用の Input / Output dataclass を持つ
  - Activity スタブ関数は raise NotImplementedError のみ
  - 実装ファイルは @activity.defn(name="<同じ名前>") で同一名を登録すること
  - フィールド追加は末尾に default 付きで追加する（後方互換）

Activity 一覧:
  1. analyze_video_content    ─ 動画を外部 AI に送信して要約・トピックを取得
  2. generate_video_metadata  ─ 要約 + プロンプトから動画メタ情報を生成
"""
from __future__ import annotations

from dataclasses import dataclass, field

from temporalio import activity


# ─────────────────────────────────────────────────────────────
# 1. analyze_video_content  ─ 動画要約取得
# ─────────────────────────────────────────────────────────────

@dataclass
class AnalyzeVideoContentInput:
    """外部 AI に送信して動画を解析するための入力。"""
    job_id: str
    video_url: str


@dataclass
class AnalyzeVideoContentOutput:
    """
    外部 AI が返す動画解析結果。
    summary はメタ情報生成の入力として次の Activity に渡す。
    """
    summary: str
    detected_topics: list[str] = field(default_factory=list)


@activity.defn
async def analyze_video_content(
    input: AnalyzeVideoContentInput,
) -> AnalyzeVideoContentOutput:
    raise NotImplementedError


# ─────────────────────────────────────────────────────────────
# 2. generate_video_metadata  ─ 動画メタ情報生成
# ─────────────────────────────────────────────────────────────

@dataclass
class GenerateVideoMetadataInput:
    """
    外部 AI に動画メタ情報を生成させるための入力。
    video_summary  : analyze_video_content の出力
    prompt_text    : 動画生成時に使用したプロンプト本文
    language       : 生成するメタ情報の言語（デフォルト: 日本語）
    """
    job_id: str
    video_summary: str
    prompt_text: str
    language: str = "ja"


@dataclass
class GenerateVideoMetadataOutput:
    """
    外部 AI が生成した動画メタ情報。
    プラットフォーム非依存の汎用形式で返す。
    category は人間可読な文字列（例: "Education"）。
    プラットフォーム固有の ID への変換は呼び出し側が行う。
    """
    title: str
    description: str
    tags: list[str] = field(default_factory=list)
    category: str = "Entertainment"


@activity.defn
async def generate_video_metadata(
    input: GenerateVideoMetadataInput,
) -> GenerateVideoMetadataOutput:
    raise NotImplementedError
