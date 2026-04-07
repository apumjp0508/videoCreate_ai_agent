"""
video_metadata pipeline  ─  独立・再利用可能な処理モジュール群。

各モジュールは Temporal / Django に依存しない純粋な処理を担う。
単体テストや別サービスからも直接呼び出せる。

  audio_extractor  ─ ffmpeg で動画から音声を抽出
  transcriber      ─ OpenAI Whisper API で音声を文字起こし
  summarizer       ─ OpenAI GPT API で文字起こしを要約・トピック抽出
"""
