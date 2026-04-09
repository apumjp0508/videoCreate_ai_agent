#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

echo "SCRIPT_DIR = $SCRIPT_DIR"
echo "ROOT_DIR   = $ROOT_DIR"

ENV_FILE="$ROOT_DIR/environment/staging/.env"
COMPOSE_FILE="$ROOT_DIR/environment/staging/docker-compose.yml"

echo "📄 環境ファイルを確認中..."
if [ ! -f "$ENV_FILE" ]; then
  echo "❌ $ENV_FILE が見つかりません。"
  exit 1
fi

echo "🧹 既存の Docker 環境を削除中..."
docker compose -f "$COMPOSE_FILE" down -v || true

echo "🔨 ビルド & 起動..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up --build -d

echo "⏳ DB の起動を待機中..."
TIMEOUT=60
ELAPSED=0
until docker compose -f "$COMPOSE_FILE" exec db pg_isready -q 2>/dev/null; do
  if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
    echo "❌ DB が ${TIMEOUT}s 以内に起動しませんでした。"
    docker compose -f "$COMPOSE_FILE" logs db
    exit 1
  fi
  echo "  waiting... (${ELAPSED}s)"
  sleep 3
  ELAPSED=$((ELAPSED + 3))
done
echo "  DB ready (${ELAPSED}s)"

echo "🗄️  マイグレーションを実行中..."
docker compose -f "$COMPOSE_FILE" exec web python manage.py migrate

echo "🌱 初期データを投入中..."
docker compose -f "$COMPOSE_FILE" exec web python manage.py seed_staging

echo "✅ 起動完了"
echo ""
echo "=== Django Web サーバー ==="
echo "  Backend:   http://localhost:8001"
echo ""
echo "=== Temporal ==="
echo "  UI:        http://localhost:8081   (ワークフロー実行状況の確認)"
echo "  gRPC:      localhost:7234          (Worker / Client の接続先)"
echo ""
echo "  Worker ログを確認するには:"
echo "    docker compose -f environment/staging/docker-compose.yml logs -f temporal-worker"
echo ""
echo "👤 管理者ユーザー"
echo "  メールアドレス / パスワードは environment/staging/.env の"
echo "  STAGING_ADMIN_EMAIL / STAGING_ADMIN_PASSWORD を参照"
echo ""
echo "🤖 AI プロバイダー / モデル (seed_ai_models)"
echo "  Runway    : gen3a_turbo, gen3a"
echo "  Kling AI  : kling-v1, kling-v1-5, kling-v2-master"
echo "  Pika      : pika-2.2 (active), pika-2.1 (inactive)"
echo "  Luma AI   : dream-machine, ray2-flash"
echo ""
echo "🔐 管理画面"
echo "  http://localhost:8001/admin-panel/"
