"""Host-side bridge server for Apple Notes interaction (runs on macOS host)."""

import json
import os
import sys
from pathlib import Path
from typing import Optional

# Add src to path for imports
_project_root = Path(__file__).parent.parent.parent
if (_project_root / "src").exists():
    sys.path.insert(0, str(_project_root / "src"))
else:
    sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from fastapi import FastAPI, HTTPException, Header
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
except ImportError:
    print(
        "Error: FastAPI and pydantic are required. Install with: pip install fastapi uvicorn pydantic",
        file=sys.stderr,
    )
    sys.exit(1)

from notes_mcp.applescript import create_note

app = FastAPI(title="Notes MCP Bridge Service")


class CreateNoteRequest(BaseModel):
    title: str
    body: str
    folder: Optional[str] = None
    account: Optional[str] = None
    tags: Optional[list[str]] = None


def verify_token(authorization: Optional[str] = Header(None)) -> bool:
    """Verify the bridge authentication token."""
    if not authorization:
        return False
    
    # Extract token from "Bearer <token>"
    if not authorization.startswith("Bearer "):
        return False
    
    token = authorization[7:]  # Remove "Bearer "
    expected_token = os.environ.get("NOTES_MCP_BRIDGE_TOKEN")
    
    if not expected_token:
        return False
    
    return token == expected_token


@app.post("/create")
async def create_note_endpoint(
    request: CreateNoteRequest,
    authorization: Optional[str] = Header(None),
):
    """Create a note in Apple Notes."""
    if not verify_token(authorization):
        raise HTTPException(status_code=401, detail="Invalid or missing authorization token")
    
    success, error_msg, result = create_note(
        title=request.title,
        body=request.body,
        folder=request.folder,
        account=request.account,
        tags=request.tags,
    )
    
    if not success:
        raise HTTPException(status_code=500, detail=error_msg or "Failed to create note")
    
    return JSONResponse(content=result or {})


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "notes-mcp-bridge"}


def main():
    """Run the bridge server."""
    import uvicorn
    
    port = int(os.environ.get("NOTES_MCP_BRIDGE_PORT", "8444"))
    host = os.environ.get("NOTES_MCP_BRIDGE_HOST", "127.0.0.1")
    
    print(f"Starting Notes MCP Bridge Service on {host}:{port}")
    print("This service handles Apple Notes interaction for containerized workers.")
    
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
