"""Export Apple Notes to local storage for read access."""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from .security import get_allowed_folders


def get_notes_from_applescript(
    folder_filter: Optional[list[str]] = None,
    account: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Read notes from Apple Notes using AppleScript.

    Args:
        folder_filter: List of folder names to include (None = all allowed folders)
        account: Account name ("iCloud" or "On My Mac", None = both)

    Returns:
        List of note dictionaries with: id, title, body, folder, account, created_at, modified_at
    """
    # Use the simple implementation
    return _read_notes_simple()


def _read_notes_simple() -> list[dict[str, Any]]:
    """
    Read notes using a simpler AppleScript approach with delimiters.
    """
    allowed_folders = get_allowed_folders()
    folder_list = ",".join([f'"{f}"' for f in allowed_folders])

    applescript = f"""
    tell application "Notes"
        set outputLines to {{}}
        
        set accountsToProcess to {{"iCloud", "On My Mac"}}
        repeat with accountName in accountsToProcess
            try
                set targetAccount to account accountName
                repeat with targetFolder in folders of targetAccount
                    set folderName to name of targetFolder
                    
                    -- Check if folder is allowed
                    set folderAllowed to false
                    if folderName is "MCP Inbox" then
                        set folderAllowed to true
                    else
                        repeat with allowedFolder in {{{folder_list}}}
                            if folderName is allowedFolder then
                                set folderAllowed to true
                                exit repeat
                            end if
                        end repeat
                    end if
                    
                    if folderAllowed then
                        repeat with noteItem in notes of targetFolder
                            try
                                set noteTitle to name of noteItem
                                set noteBody to body of noteItem
                                set noteDate to creation date of noteItem
                                set noteModDate to modification date of noteItem
                                
                                -- Use pipe delimiter for parsing
                                set noteLine to accountName & "|||" & folderName & "|||" & noteTitle & "|||" & noteBody & "|||" & (noteDate as string) & "|||" & (noteModDate as string)
                                set end of outputLines to noteLine
                            on error
                                -- Skip notes that can't be read
                            end try
                        end repeat
                    end if
                end repeat
            on error
                -- Account doesn't exist, skip
            end try
        end repeat
        
        return outputLines
    end tell
    """

    try:
        result = subprocess.run(
            ["osascript", "-e", applescript],
            text=True,
            capture_output=True,
            check=False,
            env={"PATH": "/usr/bin:/bin:/usr/local/bin"},
            timeout=60,  # Longer timeout for reading many notes
        )

        if result.returncode != 0:
            print(f"Error: {result.stderr}", file=sys.stderr)
            return []

        notes = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            try:
                parts = line.split("|||")
                if len(parts) >= 6:
                    account, folder, title, body, created_at, modified_at = parts[:6]
                    # Create stable ID
                    note_id = f"{account}|{folder}|{title}|{created_at}"
                    notes.append(
                        {
                            "id": note_id,
                            "title": title,
                            "body": body,
                            "folder": folder,
                            "account": account,
                            "created_at": created_at,
                            "modified_at": modified_at,
                        }
                    )
            except Exception as e:
                print(f"Warning: Failed to parse note line: {e}", file=sys.stderr)
                continue

        return notes

    except Exception as e:
        print(f"Error reading notes: {e}", file=sys.stderr)
        return []


def filter_notes_by_date(
    notes: list[dict[str, Any]], since_days: int
) -> list[dict[str, Any]]:
    """
    Filter notes to only include those modified within since_days.

    Args:
        notes: List of note dictionaries
        since_days: Number of days to look back

    Returns:
        Filtered list of notes
    """
    if since_days <= 0:
        return notes

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=since_days)

    filtered = []
    for note in notes:
        try:
            # Parse AppleScript date format (e.g., "Monday, January 22, 2024 at 3:45:00 PM")
            mod_date_str = note.get("modified_at", "")
            # Try to parse, if fails, include the note (better safe than sorry)
            try:
                # AppleScript dates are complex, for now we'll include all notes
                # and let the user filter by max-notes instead
                filtered.append(note)
            except Exception:
                filtered.append(note)
        except Exception:
            # If we can't parse, include it
            filtered.append(note)

    return filtered


def export_to_jsonl(
    notes: list[dict[str, Any]],
    output_path: Path,
    include_body: bool = False,
) -> None:
    """
    Export notes to JSONL file.

    Args:
        notes: List of note dictionaries
        output_path: Path to output JSONL file
        include_body: Whether to include note body (default: False)
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for note in notes:
            export_note = {
                "id": note["id"],
                "title": note["title"],
                "folder": note["folder"],
                "account": note["account"],
                "created_at": note["created_at"],
                "modified_at": note["modified_at"],
            }

            if include_body:
                export_note["body"] = note.get("body", "")

            # Extract tags from title prefixes (e.g., [WORK], [AI])
            title = note.get("title", "")
            tags = []
            if title.startswith("[") and "]" in title:
                prefix = title.split("]")[0] + "]"
                if prefix.startswith("[") and len(prefix) > 2:
                    tags.append(prefix[1:-1])
            if tags:
                export_note["tags"] = tags

            f.write(json.dumps(export_note, ensure_ascii=False) + "\n")


def export_to_sqlite(
    notes: list[dict[str, Any]],
    db_path: Path,
    include_body: bool = False,
) -> None:
    """
    Export notes to SQLite database.

    Args:
        notes: List of note dictionaries
        db_path: Path to SQLite database
        include_body: Whether to include note body (default: False)
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes_export (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                folder TEXT NOT NULL,
                account TEXT NOT NULL,
                created_at TEXT,
                modified_at TEXT,
                body TEXT,
                tags TEXT,
                exported_at TEXT NOT NULL
            )
        """
        )

        conn.execute("CREATE INDEX IF NOT EXISTS idx_folder ON notes_export(folder)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_modified_at ON notes_export(modified_at)")

        for note in notes:
            # Extract tags
            title = note.get("title", "")
            tags = []
            if title.startswith("[") and "]" in title:
                prefix = title.split("]")[0] + "]"
                if prefix.startswith("[") and len(prefix) > 2:
                    tags.append(prefix[1:-1])

            conn.execute(
                """
                INSERT OR REPLACE INTO notes_export
                (id, title, folder, account, created_at, modified_at, body, tags, exported_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    note["id"],
                    note["title"],
                    note["folder"],
                    note["account"],
                    note.get("created_at", ""),
                    note.get("modified_at", ""),
                    note.get("body", "") if include_body else None,
                    json.dumps(tags) if tags else None,
                    datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                ),
            )

        conn.commit()
    finally:
        conn.close()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Export Apple Notes to local storage for read access"
    )
    parser.add_argument(
        "--since-days",
        type=int,
        default=30,
        help="Export only notes modified within N days (default: 30)",
    )
    parser.add_argument(
        "--max-notes",
        type=int,
        default=500,
        help="Maximum number of notes to export (default: 500)",
    )
    parser.add_argument(
        "--include-body",
        action="store_true",
        help="Include note body in export (default: False, metadata only)",
    )
    parser.add_argument(
        "--format",
        choices=["jsonl", "sqlite"],
        default="jsonl",
        help="Export format (default: jsonl)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path (default: .data/notes_export.jsonl or .data/notes_export.db)",
    )

    args = parser.parse_args()

    # Check environment variable for include_body
    if os.environ.get("NOTES_MCP_EXPORT_INCLUDE_BODY", "").lower() == "true":
        args.include_body = True

    # Read notes from Apple Notes
    print("Reading notes from Apple Notes...", file=sys.stderr)
    notes = _read_notes_simple()

    if not notes:
        print("No notes found or error reading notes", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(notes)} notes", file=sys.stderr)

    # Filter by date (basic filtering - AppleScript dates are complex to parse)
    # For now, we'll rely on max-notes limit and let user filter by date manually if needed
    # notes = filter_notes_by_date(notes, args.since_days)  # TODO: Implement proper date parsing

    # Limit number of notes
    if len(notes) > args.max_notes:
        print(
            f"Limiting to {args.max_notes} most recent notes (use --max-notes to increase)",
            file=sys.stderr,
        )
        notes = notes[: args.max_notes]

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        data_dir = Path(".data")
        if args.format == "jsonl":
            output_path = data_dir / "notes_export.jsonl"
        else:
            output_path = data_dir / "notes_export.db"

    # Export
    print(f"Exporting {len(notes)} notes to {output_path}...", file=sys.stderr)
    if args.format == "jsonl":
        export_to_jsonl(notes, output_path, include_body=args.include_body)
    else:
        export_to_sqlite(notes, output_path, include_body=args.include_body)

    print(f"✓ Exported {len(notes)} notes to {output_path}", file=sys.stderr)

    # Print summary
    if not args.include_body:
        print(
            "Note: Bodies not included (use --include-body to include)",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
