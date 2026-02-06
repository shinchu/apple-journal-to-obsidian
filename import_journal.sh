#!/bin/bash
# Apple Journal → Obsidian デイリーノート統合
# dry-runでプレビュー → 確認 → 実行

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/import_journal.py"
SOURCE_DIR="${1:?ソースディレクトリを指定してください（例: ~/Downloads/AppleJournalEntries）}"

echo "=== Apple Journal → Obsidian インポート ==="
echo ""

# Step 1: dry-run
echo "--- プレビュー (dry-run) ---"
python3 "$PYTHON_SCRIPT" --source "$SOURCE_DIR" --dry-run
echo ""

# Step 2: 確認
read -rp "実行しますか？ (y/N): " answer
if [[ "$answer" != "y" && "$answer" != "Y" ]]; then
    echo "キャンセルしました"
    exit 0
fi

# Step 3: 実行
echo ""
echo "--- 実行中 ---"
python3 "$PYTHON_SCRIPT" --source "$SOURCE_DIR"
echo ""
echo "完了！"
