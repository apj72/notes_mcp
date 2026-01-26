"""Tailnet-only ingress API for enqueueing note creation jobs."""

import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional

# Add src to path for imports
_project_root = Path(__file__).parent.parent.parent
if (_project_root / "src").exists():
    sys.path.insert(0, str(_project_root / "src"))
else:
    sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from fastapi import FastAPI, HTTPException, Header, Request
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field, field_validator
except ImportError:
    print(
        "Error: FastAPI and pydantic are required. Install with: pip install fastapi uvicorn pydantic",
        file=sys.stderr,
    )
    sys.exit(1)

from notes_mcp.enqueue_job import append_to_queue
from notes_mcp.pull_worker import get_gist_id
from notes_mcp.security import (
    MAX_BODY_LENGTH,
    MAX_TITLE_LENGTH,
    get_allowed_folders,
    is_folder_allowed,
)
from notes_mcp.sign_job import create_job

# Rate limiting: track by client IP (simple approach)
_rate_limit_tracker: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
MAX_REQUESTS_PER_MINUTE = 30  # More lenient than worker (30/min vs 10/min)


def get_client_ip(request: Request) -> str:
    """Get client IP address for rate limiting."""
    # Check X-Forwarded-For (from Tailscale)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    # Fallback to direct connection
    if request.client:
        return request.client.host
    return "unknown"


def check_ingress_rate_limit(client_ip: str) -> tuple[bool, Optional[str]]:
    """
    Check if request is within rate limits.

    Args:
        client_ip: Client IP address

    Returns:
        Tuple of (allowed, error_message)
    """
    now = time.time()
    timestamps = _rate_limit_tracker[client_ip]

    # Remove old timestamps
    timestamps[:] = [ts for ts in timestamps if now - ts < RATE_LIMIT_WINDOW]

    if len(timestamps) >= MAX_REQUESTS_PER_MINUTE:
        return False, f"Rate limit exceeded: max {MAX_REQUESTS_PER_MINUTE} requests per minute"

    timestamps.append(now)
    return True, None


def verify_ingress_key(provided_key: Optional[str]) -> bool:
    """
    Verify optional ingress key from header.

    Args:
        provided_key: Key from X-Notes-MCP-Key header

    Returns:
        True if key is valid or not required, False otherwise
    """
    expected_key = os.environ.get("NOTES_MCP_INGRESS_KEY")
    if not expected_key:
        # Key not configured, allow all (rely on Tailnet ACLs)
        return True
    if not provided_key:
        return False
    return provided_key == expected_key


app = FastAPI(
    title="Notes MCP Ingress API",
    description="Tailnet-only API for enqueueing note creation jobs",
    version="0.1.0",
)


class NoteCreateRequest(BaseModel):
    """Request model for creating a note."""

    title: str = Field(..., min_length=1, max_length=MAX_TITLE_LENGTH)
    body: str = Field(..., min_length=1, max_length=MAX_BODY_LENGTH)
    folder: Optional[str] = Field(None, max_length=200)
    account: Optional[str] = Field(None, pattern="^(iCloud|On My Mac)$")
    confirm: bool = Field(default=False)

    @field_validator("title", "body")
    @classmethod
    def validate_no_null_bytes(cls, v: str) -> str:
        """Ensure no null bytes in title or body."""
        if "\x00" in v:
            raise ValueError("Title and body cannot contain null bytes")
        return v


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "notes-mcp-ingress"}


@app.get("/debug/folders")
async def debug_folders():
    """Debug endpoint to show allowed folders (for troubleshooting)."""
    from notes_mcp.security import get_allowed_folders
    
    allowed = get_allowed_folders()
    env_value = os.environ.get("NOTES_MCP_ALLOWED_FOLDERS", "(not set)")
    
    return {
        "NOTES_MCP_ALLOWED_FOLDERS_env": env_value,
        "parsed_folders": allowed,
        "count": len(allowed),
    }


@app.get("/debug/key")
async def debug_key():
    """Debug endpoint to check if ingress key is loaded (shows first/last 4 chars only)."""
    key = os.environ.get("NOTES_MCP_INGRESS_KEY", "(not set)")
    if key and key != "(not set)":
        # Show only first 4 and last 4 chars for security
        masked = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "***"
        return {
            "key_loaded": True,
            "key_length": len(key),
            "key_preview": masked,
        }
    return {
        "key_loaded": False,
        "key_value": key,
    }


@app.post("/notes")
async def create_note(
    request: NoteCreateRequest,
    http_request: Request,
    x_notes_mcp_key: Optional[str] = Header(None, alias="X-Notes-MCP-Key"),
):
    """
    Create a note by enqueueing a job to the Gist queue.

    Args:
        request: Note creation request
        http_request: FastAPI request object (for IP tracking)
        x_notes_mcp_key: Optional ingress key from header

    Returns:
        JSON response with job_id and status
    """
    # Verify optional ingress key
    if not verify_ingress_key(x_notes_mcp_key):
        raise HTTPException(status_code=401, detail="Invalid or missing X-Notes-MCP-Key header")

    # Rate limiting
    client_ip = get_client_ip(http_request)
    allowed, error = check_ingress_rate_limit(client_ip)
    if not allowed:
        raise HTTPException(status_code=429, detail=error)

    # Validate folder
    folder = request.folder or "MCP Inbox"
    if not is_folder_allowed(folder):
        raise HTTPException(
            status_code=403,
            detail=f"Folder '{folder}' is not in allowed folders list",
        )

    # Validate account
    account = request.account or "iCloud"

    # Check if confirmation is required
    require_confirm = os.environ.get("NOTES_MCP_REQUIRE_CONFIRM", "").lower() == "true"
    if require_confirm and not request.confirm:
        raise HTTPException(
            status_code=400,
            detail="Confirmation required (set confirm: true)",
        )

    # Get Gist ID
    gist_id = get_gist_id()
    if not gist_id:
        raise HTTPException(
            status_code=500,
            detail="NOTES_QUEUE_GIST_ID environment variable is not set",
        )

    # Create signed job
    try:
        job_line = create_job(
            title=request.title,
            body=request.body,
            folder=folder,
            account=account,
            confirm=request.confirm,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create job: {str(e)}",
        )

    # Enqueue to Gist
    try:
        success = append_to_queue(gist_id, job_line)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to enqueue job to Gist",
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enqueue job: {str(e)}",
        )

    # Parse job_id from job_line
    import json

    job_data = json.loads(job_line)
    job_id = job_data.get("job_id", "unknown")

    return JSONResponse(
        status_code=202,  # Accepted (queued, not yet processed)
        content={
            "status": "queued",
            "job_id": job_id,
            "message": "Note creation job enqueued successfully",
            "folder": folder,
            "account": account,
        },
    )


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("NOTES_MCP_INGRESS_HOST", "127.0.0.1")
    port = int(os.environ.get("NOTES_MCP_INGRESS_PORT", "8443"))

    uvicorn.run(app, host=host, port=port, log_level="info")
