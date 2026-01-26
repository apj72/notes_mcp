#!/bin/bash
# Generate a secure ingress key for Notes MCP
# Usage: ./scripts/generate-ingress-key.sh

echo "Generating secure ingress key..."
KEY=$(openssl rand -hex 32)

echo ""
echo "Generated key:"
echo "$KEY"
echo ""
echo "Add this to your start_worker.sh:"
echo "  export NOTES_MCP_INGRESS_KEY=\"$KEY\""
echo ""
echo "⚠️  Keep this key secret! It's used to authenticate requests to your public API."
echo ""
echo "Copy the key above and replace REPLACE_WITH_GENERATED_KEY in start_worker.sh"
