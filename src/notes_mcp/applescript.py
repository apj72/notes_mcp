"""AppleScript integration for creating notes in Apple Notes."""

import subprocess
import json
from typing import Optional


def escape_applescript_string(s: str) -> str:
    """
    Escape a string for safe use in AppleScript using JSON encoding.

    This prevents injection by using JSON encoding which handles all
    special characters safely.

    Args:
        s: String to escape

    Returns:
        JSON-encoded string safe for AppleScript
    """
    # Use JSON encoding to safely escape the string
    # This handles all special characters including quotes, backslashes, newlines, etc.
    return json.dumps(s)


def create_note(
    title: str,
    body: str,
    folder: Optional[str] = None,
    account: Optional[str] = None,
) -> tuple[bool, Optional[str], Optional[dict]]:
    """
    Create a note in Apple Notes using AppleScript.

    Args:
        title: Note title
        body: Note body
        folder: Target folder (default: "MCP Inbox")
        account: Target account ("iCloud" or "On My Mac", default: "iCloud")

    Returns:
        Tuple of (success, error_message, result_dict)
        result_dict contains: {account, folder, reference}
    """
    if folder is None:
        folder = "MCP Inbox"
    if account is None:
        account = "iCloud"

    # Escape inputs using JSON encoding to prevent injection
    # This safely handles all special characters
    title_escaped = escape_applescript_string(title)
    body_escaped = escape_applescript_string(body)
    folder_escaped = escape_applescript_string(folder)
    account_escaped = escape_applescript_string(account)

    # Build AppleScript with JSON-encoded strings
    # The JSON encoding ensures no injection is possible
    applescript = f"""
    tell application "Notes"
        activate
        
        -- Parse JSON-encoded strings (they're already properly escaped)
        set titleText to {title_escaped} as string
        set bodyText to {body_escaped} as string
        set folderName to {folder_escaped} as string
        set accountName to {account_escaped} as string
        
        -- Determine which account to use
        if accountName is "On My Mac" then
            set targetAccount to account "On My Mac"
        else
            set targetAccount to account "iCloud"
        end if
        
        -- Check if folder exists, create if it doesn't
        try
            set targetFolder to folder folderName of targetAccount
        on error
            -- Folder doesn't exist, create it
            set targetFolder to make new folder at targetAccount with properties {{name:folderName}}
        end try
        
        -- Create the note
        set newNote to make new note at targetFolder with properties {{name:titleText, body:bodyText}}
        
        -- Generate a reference (timestamp + title for uniqueness)
        set noteRef to (current date as string) & " - " & titleText
        
        return "SUCCESS|" & accountName & "|" & folderName & "|" & noteRef
    end tell
    """

    try:
        # Use osascript -e to execute the script
        # The JSON encoding in the script ensures no injection
        result = subprocess.run(
            ["osascript", "-e", applescript],
            text=True,
            capture_output=True,
            check=False,
            env={"PATH": "/usr/bin:/bin:/usr/local/bin"},
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip()
            return False, f"AppleScript error: {error_msg}", None

        output = result.stdout.strip()
        if output.startswith("SUCCESS|"):
            # Parse success output: SUCCESS|account|folder|reference
            parts = output.split("|", 3)
            if len(parts) == 4:
                _, account_result, folder_result, reference = parts
                return (
                    True,
                    None,
                    {
                        "account": account_result,
                        "folder": folder_result,
                        "reference": reference,
                    },
                )

        return False, f"Unexpected AppleScript output: {output}", None

    except subprocess.TimeoutExpired:
        return False, "AppleScript execution timed out", None
    except Exception as e:
        return False, f"Failed to execute AppleScript: {str(e)}", None
