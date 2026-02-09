#!/usr/bin/env python3
"""Integrate Apple Journal HTML exports into Obsidian daily notes."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Environment variable name
ENV_VAULT = "JOURNAL_OBSIDIAN_VAULT"

# Marker pattern for duplicate detection
MARKER_PATTERN = re.compile(r"<!-- apple-journal: (.+?) -->")


def load_daily_notes_config(vault_dir: Path) -> dict[str, str]:
    """Load Obsidian daily notes configuration.

    Args:
        vault_dir: Root path of the Obsidian vault.

    Returns:
        {"folder": str, "template": str, "format": str} (keys not configured are omitted).
    """
    config_path = vault_dir / ".obsidian" / "daily-notes.json"
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def load_template(vault_dir: Path, template_path: str) -> str | None:
    """Load an Obsidian template file.

    Args:
        vault_dir: Root path of the Obsidian vault.
        template_path: Vault-relative template path (may omit extension).

    Returns:
        Template content, or None if not found.
    """
    candidate = vault_dir / template_path
    # Obsidian may store template paths without an extension
    if not candidate.exists() and not candidate.suffix:
        candidate = candidate.with_suffix(".md")
    if candidate.exists():
        return candidate.read_text(encoding="utf-8")
    return None


def parse_date(date_str: str) -> str:
    """Convert an English date string to YYYY-MM-DD format.

    Args:
        date_str: Date string like "Friday, December 5, 2025".

    Returns:
        Date string in "2025-12-05" format.
    """
    dt = datetime.strptime(date_str.strip(), "%A, %B %d, %Y")
    return dt.strftime("%Y-%m-%d")


def extract_entry(html_content: str, filename: str) -> dict[str, str | None]:
    """Extract date, title, and body from an HTML file.

    Args:
        html_content: Contents of the HTML file.
        filename: Filename (used as a marker for duplicate detection).

    Returns:
        {"date": "YYYY-MM-DD", "title": str | None, "body": str, "filename": str}
    """
    # Extract date from pageHeader
    date_match = re.search(
        r'<div\s+class="pageHeader">\s*(.+?)\s*</div>', html_content
    )
    if not date_match:
        raise ValueError(f"{filename}: pageHeader not found")

    date_str = parse_date(date_match.group(1))

    # Extract title (span inside div.title)
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

    # Extract body paragraphs (span inside p.p2)
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

    # Decode HTML entities (e.g. &amp; → &)
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
    """Format an entry as Markdown.

    Args:
        entry: Return value of extract_entry.

    Returns:
        Markdown string with a duplicate-detection marker.
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
    template_content: str | None = None,
) -> tuple[str, int, int]:
    """Build the content of a daily note.

    Args:
        existing_content: Existing file content (None if the file does not exist).
        entries: List of entries grouped by date.
        template_content: Obsidian template content (None if unavailable).

    Returns:
        (new file content, number of entries added, number of entries skipped)
    """
    # Collect existing markers
    existing_markers: set[str] = set()
    if existing_content:
        for m in MARKER_PATTERN.finditer(existing_content):
            existing_markers.add(m.group(1))

    # Filter out duplicate entries
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

    # Build the Apple Journal section
    formatted_entries: list[str] = []
    for entry in new_entries:
        formatted_entries.append(format_entry(entry))

    new_section = "\n\n---\n\n".join(formatted_entries)

    if existing_content:
        # Check if the existing file already has an Apple Journal section
        if "## Apple Journal" in existing_content:
            # Append to the existing section
            content = existing_content.rstrip() + "\n\n---\n\n" + new_section + "\n"
        else:
            # Add a new Apple Journal section
            content = (
                existing_content.rstrip()
                + "\n\n## Apple Journal\n\n"
                + new_section
                + "\n"
            )
    else:
        # Create a new file (use template as base if available)
        prefix = template_content.rstrip() + "\n\n" if template_content else ""
        content = (
            prefix
            + "## Apple Journal\n\n"
            + new_section
            + "\n"
        )

    return content, len(new_entries), skipped


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Integrate Apple Journal HTML exports into Obsidian daily notes"
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Path to the Apple Journal export folder",
    )
    default_vault = os.environ.get(ENV_VAULT)
    parser.add_argument(
        "--vault",
        type=Path,
        default=Path(default_vault) if default_vault else None,
        help=f"Obsidian vault path (can also be set via {ENV_VAULT} env var)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview mode (no files are written)",
    )
    args = parser.parse_args()

    source_dir: Path = args.source.expanduser()

    if args.vault is None:
        print(
            f"Error: Obsidian vault path is required.\n"
            f"  Use the --vault option or set the {ENV_VAULT} environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)

    vault_dir: Path = args.vault.expanduser()

    # Load Obsidian daily notes configuration
    daily_config = load_daily_notes_config(vault_dir)
    daily_folder = daily_config.get("folder", "Daily")
    daily_dir = vault_dir / daily_folder

    # Load template
    template_content: str | None = None
    template_path = daily_config.get("template")
    if template_path:
        template_content = load_template(vault_dir, template_path)
        if template_content:
            print(f"Template: {template_path}")
        else:
            print(f"Warning: template {template_path} not found", file=sys.stderr)

    entries_dir = source_dir / "Entries"
    if not entries_dir.is_dir():
        print(f"Error: {entries_dir} not found", file=sys.stderr)
        sys.exit(1)

    # Enumerate and parse HTML files
    html_files = sorted(entries_dir.glob("*.html"))
    if not html_files:
        print("No HTML files found", file=sys.stderr)
        sys.exit(1)

    print(f"HTML files: {len(html_files)}")

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
        print(f"\nParse errors ({len(errors)}):")
        for err in errors:
            print(err)

    print(f"Dates: {len(entries_by_date)}")
    print()

    # Create or append to daily notes for each date
    total_added = 0
    total_skipped = 0

    for date_str in sorted(entries_by_date.keys()):
        entries = entries_by_date[date_str]
        daily_file = daily_dir / f"{date_str}.md"

        existing_content: str | None = None
        if daily_file.exists():
            existing_content = daily_file.read_text(encoding="utf-8")

        new_content, added, skipped = build_daily_note(
            existing_content, entries, template_content
        )
        total_added += added
        total_skipped += skipped

        status = ""
        if added > 0:
            if existing_content:
                status = f"appended (+{added})"
            else:
                status = f"created (+{added})"
        else:
            status = f"skipped ({skipped} already exist)"

        if skipped > 0 and added > 0:
            status += f" (skipped: {skipped})"

        print(f"  {date_str}.md: {status}")

        if args.dry_run:
            # In dry-run mode, preview entry contents
            for entry in entries:
                marker = "  [exists]" if entry["filename"] in (
                    set(MARKER_PATTERN.findall(existing_content))
                    if existing_content
                    else set()
                ) else "  [new]"
                title_info = f" \"{entry['title']}\"" if entry["title"] else ""
                body_preview = (entry["body"] or "")[:50]
                if len(entry["body"] or "") > 50:
                    body_preview += "..."
                print(f"    {marker} {entry['filename']}{title_info}: {body_preview}")
        elif added > 0:
            daily_dir.mkdir(parents=True, exist_ok=True)
            daily_file.write_text(new_content, encoding="utf-8")

    print()
    print(f"Total: {total_added} added, {total_skipped} skipped")
    if args.dry_run:
        print("\n(dry-run mode: no files were written)")


if __name__ == "__main__":
    main()
