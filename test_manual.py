#!/usr/bin/env python3
"""Manual test script for notes-mcp server."""

import json
import subprocess
import os
import sys

# Set environment variables for testing
os.environ["NOTES_MCP_TOKEN"] = "test-token-123"
os.environ["NOTES_MCP_ALLOWED_FOLDERS"] = "MCP Inbox"

# Initialize request
init_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {},
}

# List tools request
list_tools_request = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {},
}

# Create note request
create_request = {
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
        "name": "notes.create",
        "arguments": {
            "title": "Test Note from MCP",
            "body": "This is a test note created via the MCP server.",
            "folder": "MCP Inbox",
            "account": "iCloud",
            "_token": "test-token-123",
        },
    },
}

if __name__ == "__main__":
    # Run server (use python3 explicitly for macOS compatibility)
    proc = subprocess.Popen(
        ["python3", "-m", "notes_mcp.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Send requests
    requests = [init_request, list_tools_request, create_request]
    for req in requests:
        proc.stdin.write(json.dumps(req) + "\n")
    proc.stdin.close()

    # Read and print responses
    print("Server responses:")
    print("-" * 60)
    for line in proc.stdout:
        if line.strip():
            try:
                response = json.loads(line)
                print(json.dumps(response, indent=2))
                print("-" * 60)
            except json.JSONDecodeError:
                print(f"Non-JSON output: {line}")

    # Wait for process to finish
    proc.wait()

    # Print any errors
    stderr_output = proc.stderr.read()
    if stderr_output:
        print("\nStderr output:")
        print(stderr_output)
