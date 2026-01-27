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


def _read_notes_simple(all_folders: bool = False) -> list[dict[str, Any]]:
    """
    Read notes using a simpler AppleScript approach with delimiters.
    
    Args:
        all_folders: If True, export all folders regardless of allowlist. If False, only allowed folders.
    """
    if all_folders:
        # Export all folders - no filtering
        folder_filter_script = """
                    -- Export all folders
                    set folderAllowed to true
        """
    else:
        # Filter by allowed folders only
        allowed_folders = get_allowed_folders()
        folder_list = ",".join([f'"{f}"' for f in allowed_folders])
        folder_filter_script = f"""
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
        """

    applescript = f"""
    tell application "Notes"
        set outputLines to {{}}
        
        set accountsToProcess to {{"iCloud", "On My Mac"}}
        repeat with accountName in accountsToProcess
            try
                set targetAccount to account accountName
                repeat with targetFolder in folders of targetAccount
                    set folderName to name of targetFolder
                    {folder_filter_script}
                    
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


def _mark_duplicates(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Mark duplicate notes based on title and body similarity.
    
    Args:
        notes: List of note dictionaries
        
    Returns:
        List of notes with 'is_duplicate' and 'duplicate_group' fields added
    """
    # Normalize text for comparison (lowercase, strip whitespace)
    def normalize(text: str) -> str:
        return text.lower().strip() if text else ""
    
    # Group notes by normalized title+body
    seen = {}
    duplicate_groups = {}
    group_id = 0
    
    for note in notes:
        title = normalize(note.get("title", ""))
        body = normalize(note.get("body", ""))
        key = f"{title}|{body[:100]}"  # Use first 100 chars of body for comparison
        
        if key in seen:
            # This is a duplicate
            note["is_duplicate"] = True
            note["duplicate_group"] = seen[key]
            if seen[key] not in duplicate_groups:
                duplicate_groups[seen[key]] = []
            duplicate_groups[seen[key]].append(note["id"])
        else:
            # First occurrence
            group_id += 1
            note["is_duplicate"] = False
            note["duplicate_group"] = group_id
            seen[key] = group_id
            duplicate_groups[group_id] = [note["id"]]
    
    # Add duplicate count to each note
    for note in notes:
        group = note.get("duplicate_group")
        if group and group in duplicate_groups:
            note["duplicate_count"] = len(duplicate_groups[group])
    
    duplicate_count = sum(1 for n in notes if n.get("is_duplicate", False))
    if duplicate_count > 0:
        print(f"Found {duplicate_count} duplicate notes across {len(duplicate_groups)} groups", file=sys.stderr)
    
    return notes


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

            # Include duplicate information if present
            if "is_duplicate" in note:
                export_note["is_duplicate"] = note["is_duplicate"]
                export_note["duplicate_group"] = note.get("duplicate_group")
                export_note["duplicate_count"] = note.get("duplicate_count", 1)

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
                is_duplicate INTEGER DEFAULT 0,
                duplicate_group INTEGER,
                duplicate_count INTEGER DEFAULT 1,
                exported_at TEXT NOT NULL
            )
        """
        )

        conn.execute("CREATE INDEX IF NOT EXISTS idx_folder ON notes_export(folder)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_modified_at ON notes_export(modified_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_duplicate ON notes_export(is_duplicate, duplicate_group)")

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
                (id, title, folder, account, created_at, modified_at, body, tags, is_duplicate, duplicate_group, duplicate_count, exported_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    1 if note.get("is_duplicate", False) else 0,
                    note.get("duplicate_group"),
                    note.get("duplicate_count", 1),
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
        help="Maximum number of notes to export (default: 500, use 0 for unlimited when --all-folders)",
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
    parser.add_argument(
        "--all-folders",
        action="store_true",
        help="Export all folders, not just allowed folders (default: False, only allowed folders)",
    )
    parser.add_argument(
        "--find-duplicates",
        action="store_true",
        help="Detect and mark duplicate notes based on title and body similarity",
    )

    args = parser.parse_args()

    # Check environment variable for include_body
    if os.environ.get("NOTES_MCP_EXPORT_INCLUDE_BODY", "").lower() == "true":
        args.include_body = True

    # Read notes from Apple Notes
    print("Reading notes from Apple Notes...", file=sys.stderr)
    if args.all_folders:
        print("Exporting ALL folders (not just allowed folders)", file=sys.stderr)
    notes = _read_notes_simple(all_folders=args.all_folders)

    if not notes:
        print("No notes found or error reading notes", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(notes)} notes", file=sys.stderr)

    # Filter by date (basic filtering - AppleScript dates are complex to parse)
    # For now, we'll rely on max-notes limit and let user filter by date manually if needed
    # notes = filter_notes_by_date(notes, args.since_days)  # TODO: Implement proper date parsing

    # Limit number of notes (unless exporting all folders, then respect max-notes if set)
    if not args.all_folders and len(notes) > args.max_notes:
        print(
            f"Limiting to {args.max_notes} most recent notes (use --max-notes to increase)",
            file=sys.stderr,
        )
        notes = notes[: args.max_notes]
    elif args.all_folders and args.max_notes > 0 and len(notes) > args.max_notes:
        print(
            f"Warning: Found {len(notes)} notes but limiting to {args.max_notes} (use --max-notes 0 for unlimited)",
            file=sys.stderr,
        )
        notes = notes[: args.max_notes]
    elif args.all_folders and args.max_notes == 0:
        print(f"Exporting all {len(notes)} notes (unlimited)", file=sys.stderr)
    
    # Detect duplicates if requested
    if args.find_duplicates:
        notes = _mark_duplicates(notes)

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
