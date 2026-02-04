"""AppleScript integration for creating notes in Apple Notes."""

import subprocess
import json
import os
import tempfile
from typing import Optional, List

# Limits for tags (hashtags appended to body for searchability)
MAX_TAGS = 20
MAX_TAG_LENGTH = 50


def escape_applescript_string(s: str, use_single_quotes: bool = False) -> str:
    """
    Escape a string for safe use in AppleScript.

    This prevents injection by properly escaping special characters
    that AppleScript interprets. Uses a robust escaping method that handles
    all edge cases including Unicode, quotes, backslashes, and control characters.

    Args:
        s: String to escape
        use_single_quotes: If True, use single quotes (allows double quotes inside without escaping)

    Returns:
        Properly escaped string safe for AppleScript (already quoted)
    """
    if not s:
        return "''" if use_single_quotes else '""'
    
    # Convert to string and handle None
    s = str(s) if s is not None else ""
    
    if use_single_quotes:
        # Use single quotes - only need to escape single quotes and backslashes
        escaped_parts = []
        for char in s:
            if char == '\\':
                escaped_parts.append('\\\\')
            elif char == "'":
                escaped_parts.append("\\'")
            elif char == '\n':
                escaped_parts.append('\\n')
            elif char == '\r':
                escaped_parts.append('\\r')
            elif char == '\t':
                escaped_parts.append('\\t')
            elif ord(char) < 32:  # Control characters
                escaped_parts.append(f'\\{oct(ord(char))[2:].zfill(3)}')
            else:
                escaped_parts.append(char)
        return f"'{"".join(escaped_parts)}'"
    else:
        # Use double quotes - escape double quotes, backslashes, etc.
        escaped_parts = []
        for char in s:
            if char == '\\':
                escaped_parts.append('\\\\')
            elif char == '"':
                escaped_parts.append('\\"')
            elif char == '\n':
                escaped_parts.append('\\n')
            elif char == '\r':
                escaped_parts.append('\\r')
            elif char == '\t':
                escaped_parts.append('\\t')
            elif ord(char) < 32:  # Control characters
                # Escape as octal
                escaped_parts.append(f'\\{oct(ord(char))[2:].zfill(3)}')
            else:
                # Regular character, add as-is
                escaped_parts.append(char)
        
        # Return as quoted string
        return f'"{"".join(escaped_parts)}"'


def convert_body_to_html(body: str) -> str:
    """
    Convert plain text body to HTML format for Apple Notes.
    
    Apple Notes stores content as HTML internally, so we need to:
    - Convert single newlines (\n) to <br> tags
    - Convert double newlines (\n\n) to paragraph breaks
    - Escape HTML special characters
    - Preserve intentional blank lines
    
    Args:
        body: Plain text body with newlines
        
    Returns:
        HTML-formatted string safe for Apple Notes
    """
    if not body:
        return ""
    
    # Escape HTML special characters first
    import html
    body = html.escape(body)
    
    # Normalize line endings to \n
    body = body.replace('\r\n', '\n').replace('\r', '\n')
    
    # Split by double newlines to identify paragraphs
    # This preserves blank lines as separate paragraphs
    paragraphs = body.split('\n\n')
    
    # Process each paragraph
    html_paragraphs = []
    for para in paragraphs:
        # Strip leading/trailing newlines but preserve content
        para = para.strip('\n')
        
        if not para:
            # Empty paragraph (blank line) - use <p></p> for spacing
            html_paragraphs.append('<p></p>')
        else:
            # Apple Notes doesn't reliably render <br> tags, so we need to
            # split by single newlines and make each line a separate paragraph
            # This preserves line breaks but changes spacing slightly
            lines = para.split('\n')
            for line in lines:
                line = line.strip()
                if line:
                    # Each line becomes its own paragraph to preserve line breaks
                    html_paragraphs.append(f'<p>{line}</p>')
                else:
                    # Empty line within paragraph - preserve as spacing
                    html_paragraphs.append('<p></p>')
    
    # Join paragraphs
    html_body = ''.join(html_paragraphs)
    
    # If no paragraphs were created (shouldn't happen, but safety check)
    if not html_body:
        html_body = '<p></p>'
    
    return html_body


def _normalize_tag(tag: str) -> str:
    """Normalize a tag to a hashtag: strip, ensure # prefix, no spaces (use _), truncate."""
    if not tag or not isinstance(tag, str):
        return ""
    t = tag.strip()
    if not t:
        return ""
    if t.startswith("#"):
        t = t[1:].strip()
    t = t.replace(" ", "_")[:MAX_TAG_LENGTH]
    return f"#{t}" if t else ""


def create_note(
    title: str,
    body: str,
    folder: Optional[str] = None,
    account: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> tuple[bool, Optional[str], Optional[dict]]:
    """
    Create a note in Apple Notes using AppleScript.

    Apple Notes does not expose tags via AppleScript. Tags are appended to the note
    body as hashtags (e.g. #work #meeting) so you can search by #tagname in Notes.

    Args:
        title: Note title
        body: Note body
        folder: Target folder (default: "MCP Inbox")
        account: Target account ("iCloud" or "On My Mac", default: "iCloud")
        tags: Optional list of tags; appended as hashtags to body for searchability

    Returns:
        Tuple of (success, error_message, result_dict)
        result_dict contains: {account, folder, reference}
    """
    if folder is None:
        folder = "MCP Inbox"
    if account is None:
        account = "iCloud"

    # Convert body to HTML format (Notes uses HTML internally)
    # Check if body already looks like HTML (starts with < and contains tags)
    # If so, use it directly; otherwise convert plain text to HTML
    if body.strip().startswith('<') and ('<' in body and '>' in body):
        # Body appears to be HTML already, use it directly
        body_html = body
    else:
        # Plain text, convert to HTML
        body_html = convert_body_to_html(body)

    # Append tags as hashtags so notes can be searched by #tagname in Apple Notes
    if tags:
        hashtags = []
        for t in tags[:MAX_TAGS]:
            ht = _normalize_tag(t)
            if ht and ht not in hashtags:
                hashtags.append(ht)
        if hashtags:
            body_html = body_html + "<p>" + " ".join(hashtags) + "</p>"
    
    # Build AppleScript that accepts arguments via command line (file-based approach)
    # This avoids all quote escaping issues - the HTML never appears in the script source
    # The arguments are passed directly to osascript, which handles them safely
    applescript = """on run argv
    set titleText to item 1 of argv
    set bodyText to item 2 of argv
    set folderName to item 3 of argv
    set accountName to item 4 of argv
    
    tell application "Notes"
        activate
        
        if accountName is "On My Mac" then
            set targetAccount to account "On My Mac"
        else
            set targetAccount to account "iCloud"
        end if
        
        try
            set targetFolder to folder folderName of targetAccount
        on error
            set folderProps to {name:folderName}
            set targetFolder to make new folder at targetAccount with properties folderProps
        end try
        
        set noteProps to {name:titleText, body:bodyText}
        set newNote to make new note at targetFolder with properties noteProps
        
        set noteRef to (current date as string) & " - " & titleText
        set accountPart to "SUCCESS|" & accountName
        set folderPart to accountPart & "|" & folderName
        set finalResult to folderPart & "|" & noteRef
        return finalResult
    end tell
end run
"""

    try:
        # Write AppleScript to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.applescript', delete=False, encoding='utf-8') as script_file:
            script_file.write(applescript)
            script_path = script_file.name
        
        try:
            # Execute the script file with arguments
            # Pass title, body_html, folder, and account as command-line arguments
            # This completely avoids quote escaping issues since the values are never in the script source
            result = subprocess.run(
                ["osascript", script_path, title, body_html, folder, account],
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
                env={"PATH": "/usr/bin:/bin:/usr/local/bin"},
            )
        finally:
            # Clean up script file
            try:
                os.unlink(script_path)
            except Exception:
                pass

        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip()
            # Check if it's a syntax error (our concern) vs runtime error (permissions/Notes not running)
            is_syntax_error = 'syntax error' in error_msg.lower() or 'script error' in error_msg.lower()
            if is_syntax_error:
                return False, f"AppleScript syntax error: {error_msg}", None
            else:
                # Runtime error (Notes app not running, permissions, etc.)
                return False, f"AppleScript runtime error: {error_msg}", None

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
