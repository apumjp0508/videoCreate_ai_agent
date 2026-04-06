#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

echo "SCRIPT_DIR = $SCRIPT_DIR"
echo "ROOT_DIR   = $ROOT_DIR"

ENV_FILE="$ROOT_DIR/environment/dev/.env"
COMPOSE_FILE="$ROOT_DIR/environment/dev/docker-compose.yml"

echo "📄 環境ファイルを確認中..."
if [ ! -f "$ENV_FILE" ]; then
  echo "❌ $ENV_FILE が見つかりません。"
  exit 1
fi

echo "🧹 既存の Worker コンテナを削除中..."
docker compose -f "$COMPOSE_FILE" rm -sf temporal-worker || true

echo "🔨 Worker をビルド & 起動中..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up --build -d temporal-worker

echo "⏳ Worker の起動ログを確認中 (10 秒)..."
sleep 10
docker compose -f "$COMPOSE_FILE" logs --tail=30 temporal-worker

echo ""
echo "✅ Temporal Worker 起動完了"
echo "Task Queue: ${TEMPORAL_TASK_QUEUE:-video-job-queue}"
echo ""
echo "ログを追跡するには:"
echo "  docker compose -f $COMPOSE_FILE logs -f temporal-worker"
