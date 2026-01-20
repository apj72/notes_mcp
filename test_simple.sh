#!/bin/bash
# Simple test script for notes-mcp server

export NOTES_MCP_TOKEN="test-token-123"
export NOTES_MCP_ALLOWED_FOLDERS="MCP Inbox"

echo "Testing initialize..."
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | python3 -m notes_mcp.server

echo ""
echo "Testing tools/list..."
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | python3 -m notes_mcp.server
