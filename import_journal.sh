#!/bin/bash
# Apple Journal → Obsidian デイリーノート統合
# dry-runでプレビュー → 確認 → 実行

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/import_journal.py"

usage() {
    echo "使い方: $0 <ソースディレクトリ> [--vault <vaultパス>]"
    echo ""
    echo "環境変数 JOURNAL_OBSIDIAN_VAULT でもvaultパスを指定できます。"
    exit 1
}

# 引数パース
SOURCE_DIR=""
VAULT_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --vault)
            VAULT_ARGS=("--vault" "${2:?--vault にパスを指定してください}")
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            if [[ -z "$SOURCE_DIR" ]]; then
                SOURCE_DIR="$1"
            else
                echo "エラー: 不明な引数: $1" >&2
                usage
            fi
            shift
            ;;
    esac
done

if [[ -z "$SOURCE_DIR" ]]; then
    echo "エラー: ソースディレクトリを指定してください" >&2
    usage
fi

echo "=== Apple Journal → Obsidian インポート ==="
echo ""

# Step 1: dry-run
echo "--- プレビュー (dry-run) ---"
python3 "$PYTHON_SCRIPT" --source "$SOURCE_DIR" "${VAULT_ARGS[@]+"${VAULT_ARGS[@]}"}" --dry-run
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
python3 "$PYTHON_SCRIPT" --source "$SOURCE_DIR" "${VAULT_ARGS[@]+"${VAULT_ARGS[@]}"}"
echo ""
echo "完了！"
