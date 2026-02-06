#!/usr/bin/env python3
"""Apple JournalのHTMLエクスポートをObsidianのデイリーノートに統合するスクリプト。"""

from __future__ import annotations

import argparse
import html
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# デフォルトのObsidian vaultパス
DEFAULT_VAULT = Path.home() / "Dropbox" / "Sync" / "Private"

# デイリーノートのテンプレート（1行目空行 + ## Memo）
DAILY_TEMPLATE = "\n## Memo\n"

# 重複検出用マーカーのパターン
MARKER_PATTERN = re.compile(r"<!-- apple-journal: (.+?) -->")


def parse_date(date_str: str) -> str:
    """英語の日付文字列をYYYY-MM-DD形式に変換する。

    Args:
        date_str: "Friday, December 5, 2025" 形式の日付文字列

    Returns:
        "2025-12-05" 形式の日付文字列
    """
    dt = datetime.strptime(date_str.strip(), "%A, %B %d, %Y")
    return dt.strftime("%Y-%m-%d")


def extract_entry(html_content: str, filename: str) -> dict[str, str | None]:
    """HTMLファイルから日付・タイトル・本文を抽出する。

    Args:
        html_content: HTMLファイルの内容
        filename: ファイル名（重複検出用マーカーに使用）

    Returns:
        {"date": "YYYY-MM-DD", "title": str | None, "body": str, "filename": str}
    """
    # pageHeaderから日付を抽出
    date_match = re.search(
        r'<div\s+class="pageHeader">\s*(.+?)\s*</div>', html_content
    )
    if not date_match:
        raise ValueError(f"{filename}: pageHeaderが見つかりません")

    date_str = parse_date(date_match.group(1))

    # タイトルを抽出（div.title内のspan）
    title: str | None = None
    title_match = re.search(
        r"<div\s+class=['\"]title['\"]>\s*</span>\s*<span\s+class=['\"]s2['\"]>"
        r"(.+?)</span>",
        html_content,
    )
    if title_match:
        title_text = title_match.group(1).strip()
        if title_text:
            title = title_text

    # 本文段落を抽出（p.p2内のspan）
    body_paragraphs: list[str] = []
    for p_match in re.finditer(
        r'<p\s+class="p2">\s*<span\s+class="s[23]">(.*?)</span>\s*</p>',
        html_content,
        re.DOTALL,
    ):
        text = p_match.group(1).strip()
        if text:
            body_paragraphs.append(text)

    body = "\n\n".join(body_paragraphs)

    # HTMLエンティティをデコード（&amp; → & など）
    if title:
        title = html.unescape(title)
    body = html.unescape(body)

    return {
        "date": date_str,
        "title": title,
        "body": body,
        "filename": filename,
    }


def format_entry(entry: dict[str, str | None]) -> str:
    """エントリーをMarkdown形式にフォーマットする。

    Args:
        entry: extract_entryの戻り値

    Returns:
        マーカー付きのMarkdown文字列
    """
    lines: list[str] = []
    lines.append(f"<!-- apple-journal: {entry['filename']} -->")

    if entry["title"]:
        lines.append(f"### {entry['title']}")
        lines.append("")

    if entry["body"]:
        lines.append(entry["body"])

    return "\n".join(lines)


def build_daily_note(
    existing_content: str | None,
    entries: list[dict[str, str | None]],
) -> tuple[str, int, int]:
    """デイリーノートの内容を構築する。

    Args:
        existing_content: 既存のファイル内容（なければNone）
        entries: 日付でグループ化されたエントリーのリスト

    Returns:
        (新しいファイル内容, 追加されたエントリー数, スキップされたエントリー数)
    """
    # 既存のマーカーを収集
    existing_markers: set[str] = set()
    if existing_content:
        for m in MARKER_PATTERN.finditer(existing_content):
            existing_markers.add(m.group(1))

    # 新規エントリーをフィルタリング
    new_entries: list[dict[str, str | None]] = []
    skipped = 0
    for entry in entries:
        if entry["filename"] in existing_markers:
            skipped += 1
        else:
            new_entries.append(entry)

    if not new_entries:
        content = existing_content if existing_content else ""
        return content, 0, skipped

    # Apple Journalセクションを構築
    formatted_entries: list[str] = []
    for entry in new_entries:
        formatted_entries.append(format_entry(entry))

    new_section = "\n\n---\n\n".join(formatted_entries)

    if existing_content:
        # 既存ファイルにApple Journalセクションがあるか確認
        if "## Apple Journal" in existing_content:
            # 既存セクションの末尾に追記
            content = existing_content.rstrip() + "\n\n---\n\n" + new_section + "\n"
        else:
            # Apple Journalセクションを新規追加
            content = (
                existing_content.rstrip()
                + "\n\n## Apple Journal\n\n"
                + new_section
                + "\n"
            )
    else:
        # テンプレートから新規作成
        content = (
            DAILY_TEMPLATE
            + "\n## Apple Journal\n\n"
            + new_section
            + "\n"
        )

    return content, len(new_entries), skipped


def main() -> None:
    """メイン処理。"""
    parser = argparse.ArgumentParser(
        description="Apple JournalのHTMLをObsidianデイリーノートに統合"
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Apple Journalエクスポートフォルダのパス",
    )
    parser.add_argument(
        "--vault",
        type=Path,
        default=DEFAULT_VAULT,
        help=f"Obsidian vaultパス（デフォルト: {DEFAULT_VAULT}）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="プレビューモード（書き込みなし）",
    )
    args = parser.parse_args()

    source_dir: Path = args.source.expanduser()
    vault_dir: Path = args.vault.expanduser()
    daily_dir = vault_dir / "Daily"

    entries_dir = source_dir / "Entries"
    if not entries_dir.is_dir():
        print(f"エラー: {entries_dir} が見つかりません", file=sys.stderr)
        sys.exit(1)

    # HTMLファイルを列挙してパース
    html_files = sorted(entries_dir.glob("*.html"))
    if not html_files:
        print("HTMLファイルが見つかりません", file=sys.stderr)
        sys.exit(1)

    print(f"HTMLファイル: {len(html_files)}件")

    entries_by_date: dict[str, list[dict[str, str | None]]] = defaultdict(list)
    errors: list[str] = []

    for html_file in html_files:
        try:
            html = html_file.read_text(encoding="utf-8")
            entry = extract_entry(html, html_file.name)
            entries_by_date[entry["date"]].append(entry)
        except Exception as e:
            errors.append(f"  {html_file.name}: {e}")

    if errors:
        print(f"\nパースエラー ({len(errors)}件):")
        for err in errors:
            print(err)

    print(f"日付: {len(entries_by_date)}日分")
    print()

    # 日付ごとにデイリーノートを作成/追記
    total_added = 0
    total_skipped = 0

    for date_str in sorted(entries_by_date.keys()):
        entries = entries_by_date[date_str]
        daily_file = daily_dir / f"{date_str}.md"

        existing_content: str | None = None
        if daily_file.exists():
            existing_content = daily_file.read_text(encoding="utf-8")

        new_content, added, skipped = build_daily_note(existing_content, entries)
        total_added += added
        total_skipped += skipped

        status = ""
        if added > 0:
            if existing_content:
                status = f"追記 (+{added})"
            else:
                status = f"新規 (+{added})"
        else:
            status = f"スキップ ({skipped}件は既存)"

        if skipped > 0 and added > 0:
            status += f" (スキップ: {skipped})"

        print(f"  {date_str}.md: {status}")

        if args.dry_run:
            # dry-runモードではエントリー内容をプレビュー表示
            for entry in entries:
                marker = "  [既存]" if entry["filename"] in (
                    set(MARKER_PATTERN.findall(existing_content))
                    if existing_content
                    else set()
                ) else "  [新規]"
                title_info = f" 「{entry['title']}」" if entry["title"] else ""
                body_preview = (entry["body"] or "")[:50]
                if len(entry["body"] or "") > 50:
                    body_preview += "..."
                print(f"    {marker} {entry['filename']}{title_info}: {body_preview}")
        elif added > 0:
            daily_dir.mkdir(parents=True, exist_ok=True)
            daily_file.write_text(new_content, encoding="utf-8")

    print()
    print(f"合計: {total_added}件追加, {total_skipped}件スキップ")
    if args.dry_run:
        print("\n（dry-runモード: 書き込みは行われていません）")


if __name__ == "__main__":
    main()
