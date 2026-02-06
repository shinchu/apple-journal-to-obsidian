# Apple Journal → Obsidian Daily Notes

Apple JournalからエクスポートしたHTMLファイルを、Obsidianのデイリーノートに統合するスクリプト。

## 使い方

### 1. Apple Journalからエクスポート

iPhone/MacのJournalアプリから全エントリーをエクスポートし、任意のフォルダに保存する。エクスポートすると `Entries/*.html` の構造になる。

### 2. スクリプトを実行

```bash
# プレビュー（書き込みなし）
python3 import_journal.py --source ~/Downloads/AppleJournalEntries --dry-run

# 実行
python3 import_journal.py --source ~/Downloads/AppleJournalEntries
```

または Shell wrapper を使用:

```bash
./import_journal.sh ~/Downloads/AppleJournalEntries
```

wrapper はソースディレクトリを引数で受け取り、dry-run → 確認 → 実行 の3ステップで進む。

### オプション

| オプション | 説明 | デフォルト |
|---|---|---|
| `--source` | エクスポートフォルダのパス | （必須） |
| `--vault` | Obsidian vault のパス | `~/Dropbox/Sync/Private` |
| `--dry-run` | プレビューモード | `false` |

## 動作

- `Entries/*.html` を読み込み、`div.pageHeader` の英語日付（例: "Friday, December 5, 2025"）を `YYYY-MM-DD` に変換
- ファイル名の日付ではなく pageHeader の日付を正とする（タイムゾーン差で1日ずれることがある）
- 日付ごとにデイリーノート (`Daily/YYYY-MM-DD.md`) を作成または追記
- タイトル付きエントリーは `### タイトル` として出力
- 同日の複数エントリーは `---` で区切る
- `<!-- apple-journal: filename.html -->` マーカーによる重複検出で、再実行しても同じエントリーが二重に追加されない

## 出力例

```markdown

## Memo

## Apple Journal

<!-- apple-journal: 2025-12-04.html -->
本文テキスト

---

<!-- apple-journal: 2025-12-04_(1).html -->
### タイトル

2つ目のエントリー本文
```
