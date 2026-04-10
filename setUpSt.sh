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

# ─────────────────────────────────────────
# .env の変数を更新するヘルパー関数
# ─────────────────────────────────────────
update_env() {
  local key="$1"
  local value="$2"
  local file="$3"
  if grep -q "^${key}=" "$file"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    echo "${key}=${value}" >> "$file"
  fi
}

# ─────────────────────────────────────────
# ngrok の起動と URL 取得
# ─────────────────────────────────────────
echo "🌐 ngrok を起動中..."

# 既存の ngrok プロセスを停止
pkill -f "ngrok http" 2>/dev/null || true
sleep 1

# ngrok がインストールされているか確認
if ! command -v ngrok &> /dev/null; then
  echo "❌ ngrok がインストールされていません。"
  echo "   https://ngrok.com/download からインストールし、"
  echo "   'ngrok config add-authtoken <YOUR_TOKEN>' で認証してください。"
  exit 1
fi

# ngrok をバックグラウンドで起動（ポート 8001）
ngrok http 8001 --log=stdout > /tmp/ngrok_staging.log 2>&1 &
NGROK_PID=$!

# ngrok の起動を最大30秒待つ
echo "  ngrok の起動を待機中..."
NGROK_URL=""
for i in $(seq 1 30); do
  sleep 1
  NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null \
    | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    tunnels = data.get('tunnels', [])
    https = [t['public_url'] for t in tunnels if t['public_url'].startswith('https')]
    print(https[0] if https else '')
except:
    print('')
" 2>/dev/null)
  if [ -n "$NGROK_URL" ]; then
    break
  fi
done

if [ -z "$NGROK_URL" ]; then
  echo "❌ ngrok の起動に失敗しました。ログを確認してください: /tmp/ngrok_staging.log"
  cat /tmp/ngrok_staging.log | tail -20
  exit 1
fi

NGROK_HOST=$(echo "$NGROK_URL" | sed 's|https://||')
echo "  ngrok URL: $NGROK_URL"

# .env の SITE_BASE_URL と ALLOWED_HOSTS を更新
update_env "SITE_BASE_URL" "$NGROK_URL" "$ENV_FILE"
update_env "ALLOWED_HOSTS" "localhost 127.0.0.1 $NGROK_HOST" "$ENV_FILE"

echo "  .env を更新しました"
echo "    SITE_BASE_URL=$NGROK_URL"
echo "    ALLOWED_HOSTS=localhost 127.0.0.1 $NGROK_HOST"

# ─────────────────────────────────────────
# Docker 環境の起動
# ─────────────────────────────────────────
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
echo "  Local:     http://localhost:8001"
echo "  Public:    $NGROK_URL  (Replicate等の外部サービスが使用)"
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
echo ""
echo "⚠️  ngrok セッションを終了する場合:"
echo "  kill $NGROK_PID  または  pkill -f 'ngrok http'"
