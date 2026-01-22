#!/usr/bin/env python3
"""CLI tool to enqueue a signed job to the GitHub Gist queue."""

import argparse
import json
import os
import sys
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
    DEFAULT_QUEUE_FILENAME,
    fetch_gist_files,
    get_gist_id,
    get_github_token,
)


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

        response = requests.patch(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()

        return True

    except requests.RequestException as e:
        print(f"Error updating Gist: {e}", file=sys.stderr)
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                if "message" in error_data:
                    print(f"  GitHub API error: {error_data['message']}", file=sys.stderr)
            except Exception:
                pass
        return False
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Enqueue a signed job to the notes-mcp queue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Enqueue from sign_job output (pipe)
  python3 -m notes_mcp.sign_job --title "Test" --body "Content" | python3 -m notes_mcp.enqueue_job

  # Enqueue from file
  python3 -m notes_mcp.enqueue_job < job.jsonl

  # Enqueue from stdin
  echo '{"job_id":"...","sig":"..."}' | python3 -m notes_mcp.enqueue_job
        """,
    )
    parser.add_argument(
        "job_line",
        nargs="?",
        help="JSON job line (if not provided, reads from stdin)",
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

    # Get Gist ID
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
