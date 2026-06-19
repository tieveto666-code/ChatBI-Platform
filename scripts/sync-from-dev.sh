#!/usr/bin/env bash
# 从上级开发目录同步源码到 chatbi-open-source（不修改开发目录文件）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OSS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DEV_DIR="$(cd "$OSS_DIR/.." && pwd)"

echo "开发目录: $DEV_DIR"
echo "开源包目录: $OSS_DIR"
echo ""

rsync -a --delete \
  --exclude='.env' \
  --exclude='__pycache__' \
  --exclude='.pytest_cache' \
  --exclude='data/chatbi.db' \
  --exclude='data/uploads/*' \
  --exclude='data/file_dbs/*' \
  --exclude='data/logs/*' \
  --exclude='.DS_Store' \
  "$DEV_DIR/backend/" "$OSS_DIR/backend/"

rsync -a --delete \
  --exclude='node_modules' \
  --exclude='dist' \
  --exclude='.DS_Store' \
  "$DEV_DIR/frontend/" "$OSS_DIR/frontend/"

cp "$DEV_DIR/dev-start.sh" "$OSS_DIR/dev-start.sh"
cp "$DEV_DIR/.env.example" "$OSS_DIR/.env.example"

mkdir -p "$OSS_DIR/docs"
cp "$DEV_DIR/ChatBI-API-Spec.md" "$OSS_DIR/docs/API-Spec.md"
cp "$DEV_DIR/ChatBI-PRD.md" "$OSS_DIR/docs/PRD.md"
cp "$DEV_DIR/ChatBI-后端架构设计.md" "$OSS_DIR/docs/Architecture.md"

mkdir -p "$OSS_DIR/backend/data/uploads" "$OSS_DIR/backend/data/file_dbs" "$OSS_DIR/backend/data/logs"
touch "$OSS_DIR/backend/data/uploads/.gitkeep" \
      "$OSS_DIR/backend/data/file_dbs/.gitkeep" \
      "$OSS_DIR/backend/data/logs/.gitkeep"

# 恢复开源包专用的 backend/.env.example（rsync 会覆盖为开发版）
cat > "$OSS_DIR/backend/.env.example" << 'EOF'
# ChatBI 后端环境变量
# 复制后填入真实值：cp .env.example .env

APP_NAME=ChatBI
DEBUG=true

DATABASE_URL=sqlite:///./data/chatbi.db

LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_API_BASE=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

JWT_SECRET=change-this-to-a-random-secret-at-least-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

UPLOAD_DIR=./data/uploads
FILE_DB_DIR=./data/file_dbs
MAX_UPLOAD_SIZE_MB=20

SQL_MAX_RESULT_ROWS=10000
SQL_ENABLE_QUERY_ONLY=true

LOG_LEVEL=INFO
LOG_FILE=./data/logs/chatbi.log
EOF

chmod +x "$OSS_DIR/dev-start.sh"
find "$OSS_DIR" -name '.DS_Store' -delete 2>/dev/null || true

echo ""
echo "✅ 同步完成。请检查 git status，确认未包含 .env 或密钥后再提交。"
