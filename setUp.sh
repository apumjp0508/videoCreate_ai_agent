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

echo "🗄️  マイグレーションファイルを生成中..."
docker compose -f "$COMPOSE_FILE" exec web python manage.py makemigrations

echo "🗄️  マイグレーションを実行中..."
docker compose -f "$COMPOSE_FILE" exec web python manage.py migrate

echo "🌱 モックデータを投入中..."
docker compose -f "$COMPOSE_FILE" exec web python manage.py seed_users
docker compose -f "$COMPOSE_FILE" exec web python manage.py seed_video_ai_providers

echo "✅ 起動完了"
echo "Backend:  http://localhost:8000"
echo ""
echo "👤 モックユーザー"
echo "  alice@example.com / password123  (一般ユーザー)"
echo "  bob@example.com   / password123  (一般ユーザー)"
echo "  admin@example.com / password123  (管理者)"
echo ""
echo "🔐 管理画面"
echo "  http://localhost:8000/admin-panel/"
