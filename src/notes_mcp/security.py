"""Security utilities: authentication, rate limiting, and validation."""

import os
import time
from collections import defaultdict
from typing import Optional

# Rate limiting: max 10 calls per minute per token
MAX_CALLS_PER_MINUTE = 10
RATE_LIMIT_WINDOW = 60  # seconds

# Input validation limits
MAX_TITLE_LENGTH = 200
MAX_BODY_LENGTH = 50000

# Rate limit tracking: token -> list of timestamps
_rate_limit_tracker: dict[str, list[float]] = defaultdict(list)


def get_auth_token() -> Optional[str]:
    """Get the authentication token from environment."""
    return os.environ.get("NOTES_MCP_TOKEN")


def validate_token(provided_token: Optional[str]) -> bool:
    """
    Validate that the provided token matches the expected token.

    Args:
        provided_token: Token provided by the client

    Returns:
        True if token is valid, False otherwise
    """
    expected_token = get_auth_token()
    if not expected_token:
        return False
    return provided_token == expected_token


def get_allowed_folders() -> list[str]:
    """
    Get the list of allowed folders from environment.

    Returns:
        List of allowed folder names. Always includes "MCP Inbox".
    """
    folders_str = os.environ.get("NOTES_MCP_ALLOWED_FOLDERS", "")
    folders = [f.strip() for f in folders_str.split(",") if f.strip()]
    # Always include "MCP Inbox" as default
    if "MCP Inbox" not in folders:
        folders.append("MCP Inbox")
    return folders


def is_folder_allowed(folder: Optional[str]) -> bool:
    """
    Check if a folder is in the allowlist.

    Args:
        folder: Folder name to check (None means default "MCP Inbox")

    Returns:
        True if folder is allowed, False otherwise
    """
    if folder is None:
        folder = "MCP Inbox"
    allowed = get_allowed_folders()
    return folder in allowed


def requires_confirm() -> bool:
    """Check if confirmation mode is enabled."""
    return os.environ.get("NOTES_MCP_REQUIRE_CONFIRM", "").lower() == "true"


def check_rate_limit(token: str) -> tuple[bool, Optional[str]]:
    """
    Check if the request is within rate limits.

    Args:
        token: Authentication token (used as key for rate limiting)

    Returns:
        Tuple of (allowed, error_message). If allowed is False, error_message
        contains the reason.
    """
    now = time.time()
    timestamps = _rate_limit_tracker[token]

    # Remove timestamps outside the window
    timestamps[:] = [ts for ts in timestamps if now - ts < RATE_LIMIT_WINDOW]

    if len(timestamps) >= MAX_CALLS_PER_MINUTE:
        return False, f"Rate limit exceeded: max {MAX_CALLS_PER_MINUTE} calls per minute"

    # Record this request
    timestamps.append(now)
    return True, None


def validate_title(title: str) -> tuple[bool, Optional[str]]:
    """
    Validate note title.

    Args:
        title: Title to validate

    Returns:
        Tuple of (valid, error_message)
    """
    if not isinstance(title, str):
        return False, "Title must be a string"

    if len(title) > MAX_TITLE_LENGTH:
        return False, f"Title exceeds maximum length of {MAX_TITLE_LENGTH} characters"

    if "\x00" in title:
        return False, "Title contains null bytes"

    return True, None


def validate_body(body: str) -> tuple[bool, Optional[str]]:
    """
    Validate note body.

    Args:
        body: Body to validate

    Returns:
        Tuple of (valid, error_message)
    """
    if not isinstance(body, str):
        return False, "Body must be a string"

    if len(body) > MAX_BODY_LENGTH:
        return False, f"Body exceeds maximum length of {MAX_BODY_LENGTH} characters"

    if "\x00" in body:
        return False, "Body contains null bytes"

    return True, None


def validate_create_request(
    title: str,
    body: str,
    folder: Optional[str],
    account: Optional[str],
    confirm: Optional[bool],
    token: Optional[str],
) -> tuple[bool, Optional[str]]:
    """
    Validate a complete create request.

    Args:
        title: Note title
        body: Note body
        folder: Target folder
        account: Target account
        confirm: Confirmation flag
        token: Authentication token

    Returns:
        Tuple of (valid, error_message)
    """
    # Check authentication
    if not validate_token(token):
        return False, "Invalid or missing authentication token"

    # Check rate limit
    if token:
        allowed, error = check_rate_limit(token)
        if not allowed:
            return False, error

    # Validate title
    valid, error = validate_title(title)
    if not valid:
        return False, error

    # Validate body
    valid, error = validate_body(body)
    if not valid:
        return False, error

    # Check folder allowlist
    if not is_folder_allowed(folder):
        return False, f"Folder '{folder or 'MCP Inbox'}' is not in the allowlist"

    # Check confirmation requirement
    if requires_confirm() and confirm is not True:
        return False, "Confirmation required (confirm=true) but not provided"

    # Validate account
    if account is not None and account not in ("iCloud", "On My Mac"):
        return False, f"Invalid account: {account}. Must be 'iCloud' or 'On My Mac'"

    return True, None
