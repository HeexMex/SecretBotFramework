#!/usr/bin/env bash
# Деплой Matrix бота на сервер.
#   ./deploy.sh           — мягкий (build + restart)
#   ./deploy.sh hard      — полный (down + build + up + prune)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Подтягиваем .env
if [[ -f "$SCRIPT_DIR/.env" ]]; then
  set -a
  source "$SCRIPT_DIR/.env" 2>/dev/null || true
  set +a
else
  echo "[ERROR] .env не найден. Скопируй: cp .env.example .env"
  exit 1
fi

SSH_PORT="${SSH_PORT:-22}"
SSH_HOST="${SSH_HOST:?SSH_HOST не задан в .env}"
SSH_USER="${SSH_USER:-root}"
SERVER_IP="${SSH_USER}@${SSH_HOST}"
SSH_PASSWORD="${SSH_PASSWORD:-}"
SSH_KEY="${SSH_KEY:-}"
REMOTE_DIR="${REMOTE_DIR:-/root/matrix-bot}"
MODE="${1:-soft}"

BOT_FILES=(bot.py commands.py storage.py config.py requirements.txt Dockerfile docker-compose.yml .env)

# ── SSH / SCP ─────────────────────────────────────────────────

SSHPASS_BIN=""
for p in /usr/bin/sshpass /opt/homebrew/bin/sshpass /usr/local/bin/sshpass; do
  [[ -x "$p" ]] && SSHPASS_BIN="$p" && break
done
[[ -z "$SSHPASS_BIN" ]] && SSHPASS_BIN="$(command -v sshpass 2>/dev/null || true)"

if [[ -n "$SSH_PASSWORD" && -n "$SSHPASS_BIN" ]]; then
  SSH_CMD="$SSHPASS_BIN -p $SSH_PASSWORD ssh -o StrictHostKeyChecking=accept-new -p $SSH_PORT"
  SCP_CMD="$SSHPASS_BIN -p $SSH_PASSWORD scp -o StrictHostKeyChecking=accept-new -P $SSH_PORT"
elif [[ -n "$SSH_KEY" ]]; then
  SSH_CMD="ssh -o StrictHostKeyChecking=accept-new -p $SSH_PORT -i $SSH_KEY"
  SCP_CMD="scp -o StrictHostKeyChecking=accept-new -P $SSH_PORT -i $SSH_KEY"
else
  SSH_CMD="ssh -o StrictHostKeyChecking=accept-new -p $SSH_PORT"
  SCP_CMD="scp -o StrictHostKeyChecking=accept-new -P $SSH_PORT"
fi

echo "=== Deploy Matrix Bot ==="
echo "Сервер: $SERVER_IP"
echo "Путь:   $REMOTE_DIR"
echo "Режим:  $MODE"
echo ""

# ── Загрузка файлов ──────────────────────────────────────────

$SSH_CMD "$SERVER_IP" "mkdir -p $REMOTE_DIR"

echo "--- Загрузка файлов ---"
for f in "${BOT_FILES[@]}"; do
  if [[ -f "$SCRIPT_DIR/$f" ]]; then
    echo "  $f"
    $SCP_CMD "$SCRIPT_DIR/$f" "$SERVER_IP:$REMOTE_DIR/$f"
  else
    echo "  [SKIP] $f"
  fi
done

# ── Сборка и запуск ──────────────────────────────────────────

REMOTE_SCRIPT='
set -euo pipefail
cd "'"$REMOTE_DIR"'"

touch credentials.json
mkdir -p nio_store bot_data

MATRIX_NET=$(docker network ls --format "{{.Name}}" | grep -i matrix | grep internal | head -1)
if [ -n "$MATRIX_NET" ]; then
  echo "Matrix network: $MATRIX_NET"
  sed -i "s|name: .*|name: $MATRIX_NET|" docker-compose.yml
fi

COMPOSE="docker compose"

if [[ "'"$MODE"'" == "hard" ]]; then
  echo "--- hard: down + build + up ---"
  $COMPOSE down --remove-orphans
  $COMPOSE up -d --build --remove-orphans
else
  echo "--- soft: build + up ---"
  $COMPOSE up -d --build --remove-orphans
fi

echo ""
echo "--- Очистка ---"
docker image prune -f
docker builder prune -f 2>/dev/null || true

echo ""
echo "--- Статус ---"
$COMPOSE ps

echo ""
echo "--- Логи ---"
$COMPOSE logs --tail 15
'

echo ""
$SSH_CMD "$SERVER_IP" "$REMOTE_SCRIPT"
echo ""
echo "Готово."
