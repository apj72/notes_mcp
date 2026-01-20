"""Helper script for generating signed job lines for the queue."""

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import uuid
from datetime import datetime

from .security import get_auth_token


def get_hmac_secret() -> str:
    """Get HMAC secret, preferring NOTES_QUEUE_HMAC_SECRET, falling back to NOTES_MCP_TOKEN."""
    secret = os.environ.get("NOTES_QUEUE_HMAC_SECRET") or get_auth_token()
    if not secret:
        print(
            "Error: HMAC secret required (NOTES_QUEUE_HMAC_SECRET or NOTES_MCP_TOKEN)",
            file=sys.stderr,
        )
        sys.exit(1)
    return secret


def canonicalize_job(job: dict) -> str:
    """
    Canonicalize a job for HMAC signing.

    Creates a deterministic JSON representation by:
    - Sorting keys alphabetically
    - Removing the 'sig' field
    - Using compact JSON (no spaces)

    Args:
        job: Job dictionary

    Returns:
        Canonical JSON string
    """
    # Create a copy without the signature
    canonical = {k: v for k, v in job.items() if k != "sig"}
    # Sort keys for deterministic output
    return json.dumps(canonical, sort_keys=True, separators=(",", ":"))


def sign_job(job: dict, secret: str) -> str:
    """
    Compute HMAC signature for a job.

    Args:
        job: Job dictionary (without 'sig' field)
        secret: HMAC secret

    Returns:
        Base64-encoded HMAC-SHA256 signature
    """
    canonical = canonicalize_job(job)
    signature = base64.b64encode(
        hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).digest()
    ).decode()
    return signature


def create_job(
    title: str,
    body: str,
    folder: str = None,
    account: str = None,
    confirm: bool = False,
) -> str:
    """
    Create a signed job line.

    Args:
        title: Note title
        body: Note body
        folder: Target folder (optional)
        account: Target account (optional)
        confirm: Confirmation flag (optional)

    Returns:
        JSON line string ready to paste into queue.jsonl
    """
    secret = get_hmac_secret()

    # Build job payload
    job = {
        "job_id": str(uuid.uuid4()),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "tool": "notes.create",
        "args": {
            "title": title,
            "body": body,
        },
    }

    # Add optional fields
    if folder:
        job["args"]["folder"] = folder
    if account:
        job["args"]["account"] = account
    if confirm:
        job["args"]["confirm"] = True

    # Compute and add signature
    sig = sign_job(job, secret)
    job["sig"] = sig

    # Return as JSON line
    return json.dumps(job)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate a signed job line for the notes-mcp queue"
    )
    parser.add_argument("--title", required=True, help="Note title")
    parser.add_argument("--body", required=True, help="Note body")
    parser.add_argument("--folder", help="Target folder (default: MCP Inbox)")
    parser.add_argument(
        "--account", choices=["iCloud", "On My Mac"], help="Target account (default: iCloud)"
    )
    parser.add_argument(
        "--confirm", action="store_true", help="Include confirmation flag"
    )

    args = parser.parse_args()

    job_line = create_job(
        title=args.title,
        body=args.body,
        folder=args.folder,
        account=args.account,
        confirm=args.confirm,
    )

    print(job_line)


if __name__ == "__main__":
    main()
