# Setting Up Notes MCP in Cursor

## Important Note About ChatGPT

**ChatGPT (web interface) cannot access local MCP servers.** This MCP server is designed to run locally on your Mac and can only be accessed by:
- **Cursor** (the IDE you're using)
- **Claude Desktop** (Anthropic's desktop app)
- Other local MCP clients

If you want to use this with an AI assistant, use Cursor's built-in AI features, not ChatGPT web.

## Step-by-Step Setup for Cursor

### 1. Find Your Cursor MCP Configuration File

Cursor's MCP configuration is typically located at:
- `~/.cursor/mcp.json` (most common)
- Or check Cursor Settings → MCP Servers

### 2. Get the Full Path to Your Project

```bash
cd /Users/ajoyce/git-repos/notes_mcp
pwd
```

This will show the full path (should be `/Users/ajoyce/git-repos/notes_mcp`).

### 3. Create or Edit the MCP Configuration

Create or edit `~/.cursor/mcp.json` with the following content:

```json
{
  "mcpServers": {
    "notes-mcp": {
      "command": "python3",
      "args": ["-m", "notes_mcp.server"],
      "cwd": "/Users/ajoyce/git-repos/notes_mcp",
      "env": {
        "NOTES_MCP_TOKEN": "your-secret-token-here",
        "NOTES_MCP_ALLOWED_FOLDERS": "MCP Inbox,Work,Personal",
        "NOTES_MCP_REQUIRE_CONFIRM": "false",
        "PYTHONPATH": "/Users/ajoyce/git-repos/notes_mcp/src"
      }
    }
  }
}
```

### 4. Generate a Secure Token

Replace `"your-secret-token-here"` with a secure random token:

```bash
openssl rand -hex 32
```

Copy the output and paste it in the config file.

### 5. Restart Cursor

After saving the configuration file, restart Cursor completely (quit and reopen).

### 6. Verify It's Working

In Cursor's chat/AI interface, you should now be able to use the `notes.create` tool. Try asking:

> "Create a note titled 'Test Note' with body 'This is a test' in the MCP Inbox folder"

## Alternative: Using a Wrapper Script (Recommended)

If you prefer to manage environment variables separately, create a wrapper script:

### Create the Script

```bash
mkdir -p ~/bin
cat > ~/bin/notes-mcp-server.sh << 'EOF'
#!/bin/bash
# Notes MCP Server Wrapper

# Set environment variables
export NOTES_MCP_TOKEN="your-secret-token-here"
export NOTES_MCP_ALLOWED_FOLDERS="MCP Inbox,Work,Personal"
export NOTES_MCP_REQUIRE_CONFIRM="false"

# Set PYTHONPATH to include the project
export PYTHONPATH="/Users/ajoyce/git-repos/notes_mcp/src:$PYTHONPATH"

# Activate virtual environment if it exists
if [ -f "/Users/ajoyce/git-repos/notes_mcp/venv/bin/activate" ]; then
    source /Users/ajoyce/git-repos/notes_mcp/venv/bin/activate
fi

# Run the server
exec python3 -m notes_mcp.server
EOF

chmod +x ~/bin/notes-mcp-server.sh
```

### Update Cursor Config

Then use the simpler config:

```json
{
  "mcpServers": {
    "notes-mcp": {
      "command": "/Users/ajoyce/bin/notes-mcp-server.sh"
    }
  }
}
```

## Troubleshooting

### MCP Server Not Appearing in Cursor

1. **Check the config file location**: Make sure it's at `~/.cursor/mcp.json`
2. **Check JSON syntax**: Validate your JSON is correct (no trailing commas, proper quotes)
3. **Restart Cursor**: Fully quit and reopen Cursor
4. **Check Cursor logs**: Look for MCP-related errors in Cursor's developer console

### Permission Errors

1. **Grant Automation Permission**: 
   - System Settings → Privacy & Security → Automation
   - Enable Notes for Terminal/Python

2. **Check Python Path**: Make sure `python3` is in your PATH:
   ```bash
   which python3
   ```

### Module Not Found

If you get "ModuleNotFoundError: No module named 'notes_mcp'", either:

1. **Install the package**:
   ```bash
   cd /Users/ajoyce/git-repos/notes_mcp
   python3 -m pip install -e .
   ```

2. **Or use PYTHONPATH** (already included in config above)

## Testing the Setup

After configuration, test by asking Cursor's AI:

> "Can you create a note in Apple Notes with the title 'Hello from Cursor' and body 'This note was created via MCP'?"

If it works, you should see the note appear in your Apple Notes app!
