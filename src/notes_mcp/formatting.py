"""Text formatting normalization for note bodies."""


def normalize_note_body(body: str) -> str:
    """
    Normalize note body text for reliable formatting in Apple Notes.
    
    Handles:
    - Converts literal \\n sequences to real newlines (if no real newlines exist)
    - Normalizes line endings to \\n
    - Strips trailing whitespace from lines
    - Preserves intentional blank lines
    
    Args:
        body: Raw body text (may contain literal \\n or real newlines)
        
    Returns:
        Normalized body text with consistent formatting
    """
    if not body:
        return body
    
    # Check if body contains real newlines
    has_real_newlines = "\n" in body or "\r" in body
    
    # If no real newlines but has literal \n, convert them
    if not has_real_newlines and "\\n" in body:
        # Replace literal \n with real newlines
        # Handle both \\n (escaped in string) and \n (if somehow present)
        body = body.replace("\\n", "\n")
    
    # Normalize line endings to \n (convert \r\n and \r to \n)
    body = body.replace("\r\n", "\n").replace("\r", "\n")
    
    # Split into lines, strip trailing whitespace, preserve blank lines
    lines = []
    for line in body.split("\n"):
        # Strip trailing whitespace but preserve the line itself
        # (empty lines remain empty, non-empty lines get trailing spaces removed)
        stripped = line.rstrip()
        lines.append(stripped)
    
    # Rejoin with normalized newlines
    normalized = "\n".join(lines)
    
    # Remove trailing newlines (but preserve intentional blank lines in middle)
    # Only remove trailing newlines at the very end
    while normalized.endswith("\n\n"):
        # Keep one trailing newline if there were multiple blank lines
        normalized = normalized[:-1]
    
    return normalized
