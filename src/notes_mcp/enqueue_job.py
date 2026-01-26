#!/usr/bin/env python3
"""CLI tool to enqueue a signed job to the GitHub Gist queue."""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Add src to path for imports (works when run as module or script)
_project_root = Path(__file__).parent.parent.parent
if (_project_root / "src").exists():
    sys.path.insert(0, str(_project_root / "src"))
else:
    # Fallback: assume we're in src/notes_mcp
    sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

from notes_mcp.pull_worker import (
    DEFAULT_DB_PATH,
    DEFAULT_QUEUE_FILENAME,
    execute_job,
    fetch_gist_files,
    get_gist_id,
    get_github_token,
    init_state_db,
    is_job_processed,
    mark_job_processed,
    validate_job_age,
    validate_job_schema,
    verify_job_signature,
)
from pathlib import Path


def append_to_queue(gist_id: str, job_line: str) -> bool:
    """
    Append a job line to queue.jsonl in the Gist.

    Args:
        gist_id: GitHub Gist ID
        job_line: JSON line to append (must be valid JSON and end with newline if needed)

    Returns:
        True if successful, False otherwise
    """
    token = get_github_token()
    if not token:
        print("Error: GITHUB_TOKEN environment variable is required", file=sys.stderr)
        return False

    queue_filename = os.environ.get("NOTES_QUEUE_FILENAME", DEFAULT_QUEUE_FILENAME)

    try:
        # Fetch current Gist files
        files = fetch_gist_files(gist_id)

        # Get current queue content
        if queue_filename in files:
            current_content = files[queue_filename]["content"]
            current_sha = files[queue_filename]["sha"]
        else:
            current_content = ""
            current_sha = None

        # Ensure job_line is a single line (strip any existing newlines)
        job_line = job_line.strip()

        # Validate it's valid JSON
        try:
            json.loads(job_line)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in job line: {e}", file=sys.stderr)
            return False

        # Append: ensure newline before adding
        if current_content and not current_content.endswith("\n"):
            current_content += "\n"
        new_content = current_content + job_line + "\n"

        # Update Gist
        url = f"https://api.github.com/gists/{gist_id}"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

        files_payload = {queue_filename: {"content": new_content}}
        if current_sha:
            files_payload[queue_filename]["sha"] = current_sha

        payload = {"files": files_payload}

        # Retry logic for rate limits
        max_retries = 3
        retry_delay = 1  # Start with 1 second
        
        for attempt in range(max_retries):
            response = requests.patch(url, headers=headers, json=payload, timeout=10)
            
            # Check rate limit headers
            remaining = response.headers.get("X-RateLimit-Remaining")
            if remaining:
                remaining = int(remaining)
                if remaining == 0:
                    reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                    if reset_time > 0:
                        wait_seconds = reset_time - int(time.time())
                        if wait_seconds > 0:
                            print(
                                f"Rate limit exceeded. Reset in {wait_seconds} seconds. "
                                f"Waiting...",
                                file=sys.stderr,
                            )
                            time.sleep(min(wait_seconds + 1, 60))  # Wait up to 60 seconds
                            continue
            
            # If not rate limited, check status
            if response.status_code == 403 and "rate limit" in response.text.lower():
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    print(
                        f"Rate limit hit. Retrying in {wait_time} seconds... (attempt {attempt + 1}/{max_retries})",
                        file=sys.stderr,
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    response.raise_for_status()
            
            response.raise_for_status()
            return True

        return False

    except requests.RequestException as e:
        print(f"Error updating Gist: {e}", file=sys.stderr)
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                if "message" in error_data:
                    error_msg = error_data["message"]
                    print(f"  GitHub API error: {error_msg}", file=sys.stderr)
                    
                    # Provide helpful message for rate limits
                    if "rate limit" in error_msg.lower():
                        print(
                            "  Note: GitHub API rate limit exceeded. "
                            "Wait a few minutes and try again, or check your token's rate limit.",
                            file=sys.stderr,
                        )
            except Exception:
                pass
        return False
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


def process_job_immediately(job_line: str) -> bool:
    """
    Process a job immediately without enqueueing to Gist.
    
    Args:
        job_line: JSON job line
        
    Returns:
        True if successful, False otherwise
    """
    import json
    from notes_mcp.pull_worker import DEFAULT_DB_PATH
    
    try:
        job = json.loads(job_line)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in job line: {e}", file=sys.stderr)
        return False
    
    job_id = job.get("job_id")
    if not job_id:
        print("Error: Missing job_id in job", file=sys.stderr)
        return False
    
    # Initialize state DB
    db_path = Path(os.environ.get("NOTES_QUEUE_DB", str(DEFAULT_DB_PATH)))
    init_state_db(db_path)
    
    # Check if already processed
    if is_job_processed(db_path, job_id):
        print(f"Job {job_id[:8]}... already processed (skipping)", file=sys.stderr)
        return False
    
    # Validate schema
    valid, error = validate_job_schema(job)
    if not valid:
        print(f"Error: Invalid job schema: {error}", file=sys.stderr)
        mark_job_processed(db_path, job_id, "denied")
        return False
    
    # Validate job age
    valid, error = validate_job_age(job)
    if not valid:
        print(f"Error: {error}", file=sys.stderr)
        mark_job_processed(db_path, job_id, "denied")
        return False
    
    # Verify signature
    valid, error = verify_job_signature(job)
    if not valid:
        print(f"Error: {error}", file=sys.stderr)
        mark_job_processed(db_path, job_id, "denied")
        return False
    
    # Execute job
    result = execute_job(job)
    mark_job_processed(db_path, job_id, result["status"])
    
    # Print result
    if result["status"] == "created":
        print(f"✓ Note created: {result.get('location', {}).get('folder', 'unknown')}/{result.get('reference', '')}")
        return True
    else:
        print(f"✗ Job failed: {result.get('reason', 'Unknown error')}", file=sys.stderr)
        return False


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Enqueue a signed job to the notes-mcp queue, or process immediately",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Enqueue to Gist (processed by background worker)
  python3 -m notes_mcp.sign_job --title "Test" --body "Content" | python3 -m notes_mcp.enqueue_job

  # Process immediately (bypasses queue)
  python3 -m notes_mcp.sign_job --title "Test" --body "Content" | python3 -m notes_mcp.enqueue_job --immediate

  # Enqueue from file
  python3 -m notes_mcp.enqueue_job < job.jsonl

  # Process immediately from stdin
  echo '{"job_id":"...","sig":"..."}' | python3 -m notes_mcp.enqueue_job --immediate
        """,
    )
    parser.add_argument(
        "job_line",
        nargs="?",
        help="JSON job line (if not provided, reads from stdin)",
    )
    parser.add_argument(
        "--immediate",
        action="store_true",
        help="Process job immediately instead of enqueueing to Gist",
    )

    args = parser.parse_args()

    # Get job line from argument or stdin
    if args.job_line:
        job_line = args.job_line
    else:
        job_line = sys.stdin.read().strip()

    if not job_line:
        print("Error: No job line provided", file=sys.stderr)
        sys.exit(1)

    # Process immediately if requested
    if args.immediate:
        success = process_job_immediately(job_line)
        if success:
            sys.exit(0)
        else:
            sys.exit(1)

    # Otherwise, enqueue to Gist
    gist_id = get_gist_id()
    if not gist_id:
        print("Error: NOTES_QUEUE_GIST_ID environment variable is required", file=sys.stderr)
        sys.exit(1)

    # Enqueue the job
    success = append_to_queue(gist_id, job_line)

    if success:
        print("Job enqueued successfully", file=sys.stdout)
        sys.exit(0)
    else:
        print("Failed to enqueue job", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
