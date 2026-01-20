"""Pull worker for processing note creation jobs from a GitHub Gist queue."""

import base64
import hashlib
import hmac
import json
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import requests

from .applescript import create_note
from .logging import log_action
from .security import (
    check_rate_limit,
    get_allowed_folders,
    get_auth_token,
    is_folder_allowed,
    requires_confirm,
    validate_body,
    validate_title,
)

# Default configuration
DEFAULT_POLL_SECONDS = 15
DEFAULT_QUEUE_FILENAME = "queue.jsonl"
DEFAULT_RESULTS_FILENAME = "results.jsonl"
DEFAULT_DB_PATH = Path.home() / ".notes-mcp-queue" / "worker.sqlite3"


def get_github_token() -> Optional[str]:
    """Get GitHub token from environment."""
    return os.environ.get("GITHUB_TOKEN")


def get_gist_id() -> Optional[str]:
    """Get Gist ID from environment."""
    return os.environ.get("NOTES_QUEUE_GIST_ID")


def get_hmac_secret() -> Optional[str]:
    """Get HMAC secret, preferring NOTES_QUEUE_HMAC_SECRET, falling back to NOTES_MCP_TOKEN."""
    return os.environ.get("NOTES_QUEUE_HMAC_SECRET") or get_auth_token()


def canonicalize_job(job: dict[str, Any]) -> str:
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


def verify_job_signature(job: dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Verify HMAC signature of a job.

    Args:
        job: Job dictionary with 'sig' field

    Returns:
        Tuple of (valid, error_message)
    """
    if "sig" not in job:
        return False, "Missing signature field"

    provided_sig = job["sig"]
    secret = get_hmac_secret()

    if not secret:
        return False, "HMAC secret not configured (NOTES_QUEUE_HMAC_SECRET or NOTES_MCP_TOKEN)"

    # Compute expected signature
    canonical = canonicalize_job(job)
    expected_sig = base64.b64encode(
        hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).digest()
    ).decode()

    if not hmac.compare_digest(provided_sig, expected_sig):
        return False, "Invalid HMAC signature"

    return True, None


def fetch_gist_files(gist_id: str) -> dict[str, dict[str, Any]]:
    """
    Fetch all files from a GitHub Gist.

    Args:
        gist_id: GitHub Gist ID

    Returns:
        Dictionary mapping filename -> file content dict with 'content' and 'sha' keys

    Raises:
        requests.RequestException: If API request fails
    """
    token = get_github_token()
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is required")

    url = f"https://api.github.com/gists/{gist_id}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    gist_data = response.json()
    files = {}

    for filename, file_info in gist_data.get("files", {}).items():
        files[filename] = {
            "content": file_info.get("content", ""),
            "sha": file_info.get("sha", ""),
        }

    return files


def append_gist_file(
    gist_id: str, filename: str, new_lines: list[str], expected_sha: Optional[str] = None
) -> bool:
    """
    Append lines to a Gist file.

    Implements append-only by reading existing content, appending new lines,
    and writing back. Uses optimistic concurrency with file SHA.

    Args:
        gist_id: GitHub Gist ID
        filename: Name of the file to append to
        new_lines: List of new lines (strings) to append
        expected_sha: Optional expected SHA of current file (for optimistic locking)

    Returns:
        True if successful, False otherwise
    """
    token = get_github_token()
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is required")

    # Fetch current content
    files = fetch_gist_files(gist_id)

    if filename not in files:
        # File doesn't exist, create it with new lines
        current_content = ""
        current_sha = None
    else:
        current_content = files[filename]["content"]
        current_sha = files[filename]["sha"]

        # Verify SHA if provided (optimistic concurrency)
        if expected_sha and current_sha != expected_sha:
            return False  # File was modified, retry needed

    # Append new lines
    if current_content and not current_content.endswith("\n"):
        current_content += "\n"
    new_content = current_content + "\n".join(new_lines)
    if new_lines:
        new_content += "\n"

    # Update Gist
    url = f"https://api.github.com/gists/{gist_id}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    files_payload = {filename: {"content": new_content}}
    if current_sha:
        files_payload[filename]["sha"] = current_sha

    payload = {"files": files_payload}

    response = requests.patch(url, headers=headers, json=payload, timeout=10)
    response.raise_for_status()

    return True


def init_state_db(db_path: Path) -> None:
    """
    Initialize SQLite database for tracking processed jobs.

    Args:
        db_path: Path to SQLite database file
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_jobs (
                job_id TEXT PRIMARY KEY,
                processed_at TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """
        )
        conn.commit()
    finally:
        conn.close()


def is_job_processed(db_path: Path, job_id: str) -> bool:
    """
    Check if a job has already been processed.

    Args:
        db_path: Path to SQLite database
        job_id: Job ID to check

    Returns:
        True if job has been processed, False otherwise
    """
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.execute("SELECT 1 FROM processed_jobs WHERE job_id = ?", (job_id,))
        return cursor.fetchone() is not None
    finally:
        conn.close()


def mark_job_processed(db_path: Path, job_id: str, status: str) -> None:
    """
    Mark a job as processed in the database.

    Args:
        db_path: Path to SQLite database
        job_id: Job ID
        status: Processing status ("ok", "denied", "error")
    """
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "INSERT OR REPLACE INTO processed_jobs (job_id, processed_at, status) VALUES (?, ?, ?)",
            (job_id, datetime.utcnow().isoformat() + "Z", status),
        )
        conn.commit()
    finally:
        conn.close()


def validate_job_schema(job: dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate job schema.

    Args:
        job: Job dictionary

    Returns:
        Tuple of (valid, error_message)
    """
    required_fields = ["job_id", "created_at", "tool", "args", "sig"]
    for field in required_fields:
        if field not in job:
            return False, f"Missing required field: {field}"

    if job["tool"] != "notes.create":
        return False, f"Unsupported tool: {job['tool']}"

    args = job["args"]
    if "title" not in args or "body" not in args:
        return False, "Missing required args: title and body"

    return True, None


def execute_job(job: dict[str, Any]) -> dict[str, Any]:
    """
    Execute a notes.create job using the existing internal code path.

    Args:
        job: Job dictionary

    Returns:
        Result dictionary with status, location, reference, and optional error
    """
    job_id = job["job_id"]
    args = job["args"]

    title = args.get("title", "")
    body = args.get("body", "")
    folder = args.get("folder")
    account = args.get("account")
    confirm = args.get("confirm", False)

    # Use a fixed token for rate limiting (worker token)
    # We'll use the HMAC secret as the rate limit key
    worker_token = get_hmac_secret() or "worker"

    # Validate using existing security functions
    # Note: We skip token validation since HMAC already authenticated the job
    # But we still check rate limits, folder allowlist, confirmation, etc.

    # Check rate limit
    allowed, error = check_rate_limit(worker_token)
    if not allowed:
        log_action(
            action="create",
            title_length=len(title),
            body_length=len(body),
            account=account,
            folder=folder,
            outcome="denied",
            error=error,
        )
        return {
            "job_id": job_id,
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "status": "denied",
            "error": {"code": "RATE_LIMIT", "message": error or "Rate limit exceeded"},
        }

    # Validate title
    valid, error = validate_title(title)
    if not valid:
        log_action(
            action="create",
            title_length=len(title),
            body_length=len(body),
            account=account,
            folder=folder,
            outcome="denied",
            error=error,
        )
        return {
            "job_id": job_id,
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "status": "denied",
            "error": {"code": "VALIDATION_ERROR", "message": error or "Invalid title"},
        }

    # Validate body
    valid, error = validate_body(body)
    if not valid:
        log_action(
            action="create",
            title_length=len(title),
            body_length=len(body),
            account=account,
            folder=folder,
            outcome="denied",
            error=error,
        )
        return {
            "job_id": job_id,
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "status": "denied",
            "error": {"code": "VALIDATION_ERROR", "message": error or "Invalid body"},
        }

    # Check folder allowlist
    if not is_folder_allowed(folder):
        error_msg = f"Folder '{folder or 'MCP Inbox'}' is not in the allowlist"
        log_action(
            action="create",
            title_length=len(title),
            body_length=len(body),
            account=account,
            folder=folder,
            outcome="denied",
            error=error_msg,
        )
        return {
            "job_id": job_id,
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "status": "denied",
            "error": {"code": "FOLDER_NOT_ALLOWED", "message": error_msg},
        }

    # Check confirmation requirement
    if requires_confirm() and confirm is not True:
        error_msg = "Confirmation required (confirm=true) but not provided"
        log_action(
            action="create",
            title_length=len(title),
            body_length=len(body),
            account=account,
            folder=folder,
            outcome="denied",
            error=error_msg,
        )
        return {
            "job_id": job_id,
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "status": "denied",
            "error": {"code": "CONFIRMATION_REQUIRED", "message": error_msg},
        }

    # Validate account
    if account is not None and account not in ("iCloud", "On My Mac"):
        error_msg = f"Invalid account: {account}. Must be 'iCloud' or 'On My Mac'"
        log_action(
            action="create",
            title_length=len(title),
            body_length=len(body),
            account=account,
            folder=folder,
            outcome="denied",
            error=error_msg,
        )
        return {
            "job_id": job_id,
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "status": "denied",
            "error": {"code": "INVALID_ACCOUNT", "message": error_msg},
        }

    # Execute the note creation using existing internal function
    success, error_msg, result = create_note(
        title=title,
        body=body,
        folder=folder,
        account=account,
    )

    if not success:
        log_action(
            action="create",
            title_length=len(title),
            body_length=len(body),
            account=account,
            folder=folder,
            outcome="error",
            error=error_msg,
        )
        return {
            "job_id": job_id,
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "status": "error",
            "error": {"code": "EXECUTION_ERROR", "message": error_msg or "Failed to create note"},
        }

    # Success
    log_action(
        action="create",
        title_length=len(title),
        body_length=len(body),
        account=result["account"],
        folder=result["folder"],
        outcome="allowed",
    )

    return {
        "job_id": job_id,
        "processed_at": datetime.utcnow().isoformat() + "Z",
        "status": "ok",
        "location": {
            "account": result["account"],
            "folder": result["folder"],
        },
        "reference": result["reference"],
    }


def process_queue() -> None:
    """Main worker loop: fetch jobs, process, and append results."""
    gist_id = get_gist_id()
    if not gist_id:
        print("Error: NOTES_QUEUE_GIST_ID environment variable is required", file=sys.stderr)
        sys.exit(1)

    github_token = get_github_token()
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)

    hmac_secret = get_hmac_secret()
    if not hmac_secret:
        print(
            "Error: HMAC secret required (NOTES_QUEUE_HMAC_SECRET or NOTES_MCP_TOKEN)",
            file=sys.stderr,
        )
        sys.exit(1)

    # Configuration
    poll_seconds = int(os.environ.get("NOTES_QUEUE_POLL_SECONDS", DEFAULT_POLL_SECONDS))
    queue_filename = os.environ.get("NOTES_QUEUE_FILENAME", DEFAULT_QUEUE_FILENAME)
    results_filename = os.environ.get("NOTES_RESULTS_FILENAME", DEFAULT_RESULTS_FILENAME)
    db_path = Path(os.environ.get("NOTES_QUEUE_DB", str(DEFAULT_DB_PATH)))

    # Initialize state database
    init_state_db(db_path)

    print(f"Worker started. Polling every {poll_seconds} seconds.")
    print(f"Gist ID: {gist_id}")
    print(f"Queue file: {queue_filename}")
    print(f"Results file: {results_filename}")
    print(f"State DB: {db_path}")

    while True:
        try:
            # Fetch Gist files
            files = fetch_gist_files(gist_id)

            if queue_filename not in files:
                print(f"Warning: Queue file '{queue_filename}' not found in Gist")
                time.sleep(poll_seconds)
                continue

            queue_content = files[queue_filename]["content"]
            if not queue_content.strip():
                # Empty queue, wait and continue
                time.sleep(poll_seconds)
                continue

            # Parse queue.jsonl
            processed_count = 0
            results_to_append = []

            for line in queue_content.strip().split("\n"):
                if not line.strip():
                    continue

                try:
                    job = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"Warning: Invalid JSON in queue: {e}")
                    continue

                # Validate schema
                valid, error = validate_job_schema(job)
                if not valid:
                    print(f"Warning: Invalid job schema: {error}")
                    continue

                job_id = job["job_id"]

                # Check if already processed
                if is_job_processed(db_path, job_id):
                    continue  # Skip already processed jobs

                # Verify HMAC signature
                valid, error = verify_job_signature(job)
                if not valid:
                    print(f"Warning: Invalid signature for job {job_id}: {error}")
                    # Still record as processed to prevent replay attacks
                    mark_job_processed(db_path, job_id, "denied")
                    results_to_append.append(
                        json.dumps(
                            {
                                "job_id": job_id,
                                "processed_at": datetime.utcnow().isoformat() + "Z",
                                "status": "denied",
                                "error": {"code": "INVALID_SIGNATURE", "message": error},
                            }
                        )
                    )
                    continue

                # Execute job
                result = execute_job(job)
                results_to_append.append(json.dumps(result))

                # Mark as processed
                mark_job_processed(db_path, job_id, result["status"])
                processed_count += 1

                print(f"Processed job {job_id}: {result['status']}")

            # Append results if any
            if results_to_append:
                # Get current SHA for optimistic concurrency
                current_sha = files.get(results_filename, {}).get("sha")
                success = append_gist_file(gist_id, results_filename, results_to_append, current_sha)

                if not success:
                    print("Warning: Failed to append results (concurrent modification, will retry)")

            if processed_count > 0:
                print(f"Processed {processed_count} job(s)")

        except requests.RequestException as e:
            print(f"Error fetching Gist: {e}")
        except Exception as e:
            print(f"Error processing queue: {e}")

        # Wait before next poll
        time.sleep(poll_seconds)


def main() -> None:
    """CLI entry point."""
    process_queue()


if __name__ == "__main__":
    main()
