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

echo "🧹 既存の Temporal コンテナを削除中..."
docker compose -f "$COMPOSE_FILE" rm -sf temporal temporal-ui temporal-db || true

echo "🔨 Temporal DB を起動中..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up --build -d temporal-db

echo "⏳ Temporal DB の起動を待機中..."
TIMEOUT=60
ELAPSED=0
until docker compose -f "$COMPOSE_FILE" exec temporal-db pg_isready -q 2>/dev/null; do
  if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
    echo "❌ Temporal DB が ${TIMEOUT}s 以内に起動しませんでした。"
    docker compose -f "$COMPOSE_FILE" logs temporal-db
    exit 1
  fi
  echo "  waiting... (${ELAPSED}s)"
  sleep 3
  ELAPSED=$((ELAPSED + 3))
done
echo "  Temporal DB ready (${ELAPSED}s)"

echo "🔨 Temporal サーバー & UI を起動中..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d temporal temporal-ui

echo "⏳ Temporal サーバーの起動を待機中..."
TIMEOUT=90
ELAPSED=0
until docker compose -f "$COMPOSE_FILE" exec temporal \
    tctl --address temporal:7233 cluster health >/dev/null 2>&1; do
  if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
    echo "❌ Temporal サーバーが ${TIMEOUT}s 以内に起動しませんでした。"
    docker compose -f "$COMPOSE_FILE" logs temporal
    exit 1
  fi
  echo "  waiting... (${ELAPSED}s)"
  sleep 5
  ELAPSED=$((ELAPSED + 5))
done
echo "  Temporal server ready (${ELAPSED}s)"

echo "✅ Temporal 起動完了"
echo "Temporal gRPC:  localhost:7233"
echo "Temporal UI:    http://localhost:8080"
