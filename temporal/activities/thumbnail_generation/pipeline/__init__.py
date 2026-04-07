"""
thumbnail_generation pipeline  ─  独立・再利用可能な処理モジュール群。

各モジュールは Temporal / Django に依存しない純粋な処理を担う。
単体テストや別サービスからも直接呼び出せる。

  snapshot_extractor  ─ ffmpeg で動画から1秒毎のスナップショットを抽出
  snapshot_scorer     ─ GPT Vision でスナップショットをスコアリングし最適なものを選択
"""
