"""MCP server implementation using stdio transport and JSON-RPC."""

import json
import sys
from typing import Any, Optional

from .applescript import create_note
from .formatting import normalize_note_body
from .logging import log_action
from .security import (
    validate_create_request,
    get_auth_token,
    requires_confirm,
    is_folder_allowed,
)


class MCPServer:
    """MCP server for creating notes in Apple Notes."""

    def __init__(self):
        """Initialize the MCP server."""
        # Check that token is configured
        if not get_auth_token():
            print(
                "Error: NOTES_MCP_TOKEN environment variable is not set",
                file=sys.stderr,
            )
            sys.exit(1)

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Handle an MCP request.

        Args:
            request: JSON-RPC request object

        Returns:
            JSON-RPC response object
        """
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        # Handle initialize request (MCP protocol)
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                    },
                    "serverInfo": {
                        "name": "notes-mcp",
                        "version": "0.1.0",
                    },
                },
            }

        # Handle tools/list request
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": "notes.create",
                            "description": "Create a new note in Apple Notes",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "title": {
                                        "type": "string",
                                        "description": "Note title (max 200 characters)",
                                    },
                                    "body": {
                                        "type": "string",
                                        "description": "Note body (max 50,000 characters)",
                                    },
                                    "folder": {
                                        "type": "string",
                                        "description": "Target folder (default: 'MCP Inbox')",
                                    },
                                    "account": {
                                        "type": "string",
                                        "enum": ["iCloud", "On My Mac"],
                                        "description": "Target account (default: 'iCloud')",
                                    },
                                    "confirm": {
                                        "type": "boolean",
                                        "description": "Confirmation flag (required if NOTES_MCP_REQUIRE_CONFIRM=true)",
                                    },
                                    "tags": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Optional tags; appended as hashtags to body so notes can be searched by #tagname in Apple Notes (max 20)",
                                    },
                                },
                                "required": ["title", "body"],
                            },
                        }
                    ],
                },
            }

        # Handle tools/call request
        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name == "notes.create":
                return self._handle_create_note(arguments, request_id)

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}",
                },
            }

        # Unknown method
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Unknown method: {method}",
            },
        }

    def _handle_create_note(
        self, arguments: dict[str, Any], request_id: Optional[Any]
    ) -> dict[str, Any]:
        """
        Handle a notes.create tool call.

        Args:
            arguments: Tool arguments
            request_id: JSON-RPC request ID

        Returns:
            JSON-RPC response
        """
        # Extract parameters
        title = arguments.get("title", "")
        body = arguments.get("body", "")
        folder = arguments.get("folder")
        account = arguments.get("account")
        confirm = arguments.get("confirm", False)
        tags = arguments.get("tags")
        if tags is not None and isinstance(tags, list):
            tags = [str(t).strip() for t in tags if isinstance(t, str) and str(t).strip()][:20]
            if not tags:
                tags = None
        else:
            tags = None

        # Normalize body formatting (convert literal \n to real newlines, etc.)
        # Do this BEFORE validation so validation sees the normalized body
        body = normalize_note_body(body)

        # Extract token from arguments (MCP clients can pass it in a metadata field)
        # For stdio transport, we'll check for it in a special field
        token = arguments.get("_token") or arguments.get("token")

        # Validate request
        valid, error_msg = validate_create_request(
            title=title,
            body=body,
            folder=folder,
            account=account,
            confirm=confirm,
            token=token,
        )

        # Log the attempt
        outcome = "denied" if not valid else "allowed"
        log_action(
            action="create",
            title_length=len(title),
            body_length=len(body),
            account=account,
            folder=folder,
            outcome=outcome,
            error=error_msg if not valid else None,
        )

        if not valid:
            # Check if it was a confirmation denial
            if requires_confirm() and confirm is not True:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32000,
                        "message": "Confirmation required but not provided",
                        "data": {"requires_confirm": True},
                    },
                }

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32000,
                    "message": error_msg or "Validation failed",
                },
            }

        # Create the note
        success, error_msg, result = create_note(
            title=title,
            body=body,
            folder=folder,
            account=account,
            tags=tags,
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
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32000,
                    "message": error_msg or "Failed to create note",
                },
            }

        # Log success
        log_action(
            action="create",
            title_length=len(title),
            body_length=len(body),
            account=result["account"],
            folder=result["folder"],
            outcome="allowed",
        )

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "ok": True,
                "location": {
                    "account": result["account"],
                    "folder": result["folder"],
                },
                "reference": result["reference"],
            },
        }

    def run(self) -> None:
        """Run the MCP server, reading from stdin and writing to stdout."""
        # Read requests from stdin
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
                response = self.handle_request(request)
                print(json.dumps(response))
                sys.stdout.flush()
            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}",
                    },
                }
                print(json.dumps(error_response))
                sys.stdout.flush()
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}",
                    },
                }
                print(json.dumps(error_response))
                sys.stdout.flush()


def main() -> None:
    """Main entry point."""
    server = MCPServer()
    server.run()


if __name__ == "__main__":
    main()
