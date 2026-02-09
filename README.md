# Apple Journal → Obsidian Daily Notes

Apple JournalからエクスポートしたHTMLファイルを、Obsidianのデイリーノートに統合するスクリプト。

## セットアップ

### Obsidian Vault パスの設定

環境変数 `JOURNAL_OBSIDIAN_VAULT` に Obsidian vault のパスを設定する。

```bash
# ~/.bashrc or ~/.zshrc に追記
export JOURNAL_OBSIDIAN_VAULT="$HOME/path/to/your/vault"
```

### Vault の構造

```
YourVault/
├── .obsidian/
│   └── daily-notes.json    ← Obsidian が自動生成する設定
├── Daily/                   ← デイリーノートの格納先（設定で変更可）
│   ├── 2025-12-04.md
│   ├── 2025-12-05.md
│   └── ...
├── Templates/               （任意）
│   └── Daily.md             ← デイリーノートのテンプレート
└── ...
```

スクリプトは `.obsidian/daily-notes.json` から以下を自動で読み取る:

- **`folder`** — デイリーノートの保存先フォルダ（デフォルト: `Daily`）
- **`template`** — 新規ノート作成時に使うテンプレートファイルのパス

テンプレートが設定されている場合、新規デイリーノートはテンプレートの内容をベースに作成され、末尾に Apple Journal セクションが追記される。既存のデイリーノートにはそのまま末尾に追記される。

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
| `--vault` | Obsidian vault のパス | 環境変数 `JOURNAL_OBSIDIAN_VAULT` |
| `--dry-run` | プレビューモード | `false` |

`--vault` を指定すると環境変数より優先される。どちらも未設定の場合はエラーになる。

## 動作

- `Entries/*.html` を読み込み、`div.pageHeader` の英語日付（例: "Friday, December 5, 2025"）を `YYYY-MM-DD` に変換
- ファイル名の日付ではなく pageHeader の日付を正とする（タイムゾーン差で1日ずれることがある）
- 日付ごとにデイリーノートを作成または追記
- タイトル付きエントリーは `### タイトル` として出力
- 同日の複数エントリーは `---` で区切る
- `<!-- apple-journal: filename.html -->` マーカーによる重複検出で、再実行しても同じエントリーが二重に追加されない

## 出力例

テンプレートなしの場合:

```markdown
## Apple Journal

<!-- apple-journal: 2025-12-04.html -->
本文テキスト

---

<!-- apple-journal: 2025-12-04_(1).html -->
### タイトル

2つ目のエントリー本文
```

テンプレートありの場合（テンプレートの内容の後に追記される）:

```markdown
## Memo

## Todo
- [ ]

## Apple Journal

<!-- apple-journal: 2025-12-04.html -->
本文テキスト
```
