#!/bin/bash
set -euo pipefail

# Only run in remote Claude Code environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

PARENT_DIR="$(dirname "$CLAUDE_PROJECT_DIR")/authentic-parent"

if [ -d "$PARENT_DIR/.git" ]; then
  echo "Parent theme reference already present, pulling latest..."
  git -C "$PARENT_DIR" pull --quiet
  exit 0
fi

echo "Cloning parent Authentic theme reference..."

# Reuse the same authenticated proxy as this repo's origin
ORIGIN_URL="$(git -C "$CLAUDE_PROJECT_DIR" remote get-url origin)"
PARENT_URL="${ORIGIN_URL/thethreedrinkers-wp/thethreedrinkers-parent-reference}"

git clone --quiet "$PARENT_URL" "$PARENT_DIR"
echo "Parent theme cloned to $PARENT_DIR"
