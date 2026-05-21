#!/usr/bin/env bash
# Deploy the MAAS Summit Team 8 app to Databricks Apps.
#
# Steps:
#   1. Pre-flight: confirm profile, app name, source dir
#   2. Sync source dir to workspace (excluding node_modules, .venv, etc — there shouldn't be any)
#   3. Ensure the App exists; create if not
#   4. Trigger deploy
#   5. Print app URL

set -euo pipefail

PROFILE=${DATABRICKS_PROFILE:-DEFAULT}
APP_NAME=${APP_NAME:-maas-summit-team8}
SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORKSPACE_PATH=${WORKSPACE_PATH:-/Workspace/Users/$(databricks current-user me --profile "$PROFILE" -o json | python3 -c 'import sys,json;print(json.load(sys.stdin)["userName"])')/maas-summit-team8}

echo "profile        = $PROFILE"
echo "app            = $APP_NAME"
echo "source dir     = $SRC_DIR"
echo "workspace path = $WORKSPACE_PATH"

# 1. Sync source dir
echo ""
echo "[1/3] syncing source to workspace..."
databricks sync --profile "$PROFILE" --watch=false --full \
  --exclude "**/__pycache__/**" \
  --exclude "**/.venv/**" \
  --exclude "**/node_modules/**" \
  --exclude "scripts/**" \
  --exclude ".env" \
  "$SRC_DIR" "$WORKSPACE_PATH"

# 2. Ensure app exists
echo ""
echo "[2/3] ensuring app $APP_NAME exists..."
if databricks apps get "$APP_NAME" --profile "$PROFILE" >/dev/null 2>&1; then
  echo "  app already exists"
else
  echo "  creating app..."
  databricks apps create "$APP_NAME" --profile "$PROFILE"
fi

# 3. Deploy
echo ""
echo "[3/3] deploying..."
databricks apps deploy "$APP_NAME" \
  --profile "$PROFILE" \
  --source-code-path "$WORKSPACE_PATH"

# 4. Print URL
URL=$(databricks apps get "$APP_NAME" --profile "$PROFILE" -o json | python3 -c 'import sys,json;print(json.load(sys.stdin).get("url",""))')
echo ""
echo "✓ deployed. URL: $URL"
