"""Audit logging for notes-mcp server."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

LOG_DIR = Path.home() / "Library" / "Logs" / "notes-mcp"
LOG_FILE = LOG_DIR / "notes-mcp.log"


def ensure_log_dir() -> None:
    """Ensure the log directory exists."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_action(
    action: str,
    title_length: int,
    body_length: int,
    account: Optional[str],
    folder: Optional[str],
    outcome: str,
    error: Optional[str] = None,
    remote_addr: Optional[str] = None,
) -> None:
    """
    Log an action to the audit log.

    Args:
        action: The action performed (e.g., "create")
        title_length: Length of the note title
        body_length: Length of the note body
        account: Target account name
        folder: Target folder name
        outcome: "allowed", "denied", or "error"
        error: Optional error message
        remote_addr: Optional remote address (for HTTP transport)
    """
    ensure_log_dir()

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "action": action,
        "title_length": title_length,
        "body_length": body_length,
        "account": account,
        "folder": folder,
        "outcome": outcome,
    }

    if remote_addr:
        log_entry["remote_addr"] = remote_addr

    if error:
        log_entry["error"] = error

    # Append-only log file
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")
