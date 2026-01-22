# Quick Start: Using Notes MCP with ChatGPT

## For ChatGPT: How to Create Notes

### Simple 3-Step Process

1. **Generate a signed job**:
   ```bash
   cd /Users/ajoyce/git-repos/notes_mcp
   source venv/bin/activate
   export PYTHONPATH="src:$PYTHONPATH"
   export NOTES_MCP_TOKEN="your-actual-token"
   
   python3 -m notes_mcp.sign_job \
     --title "Note Title" \
     --body "Note content" \
     --folder "MCP Inbox"
   ```

2. **Copy the JSON output** (it's a single line)

3. **Add to Gist**: 
   - Go to: `https://gist.github.com/YOUR_USERNAME/YOUR_GIST_ID` (your Gist)
   - Edit `queue.jsonl`
   - Paste the JSON line at the end
   - Save

**The note will appear in Apple Notes within 15-30 seconds** (if pull worker is running).

## Your Gist Information

- **Gist ID**: `YOUR_GIST_ID` (your actual Gist ID)
- **Gist URL**: `https://gist.github.com/YOUR_USERNAME/YOUR_GIST_ID`
- **Queue file**: `queue.jsonl`
- **Results file**: `results.jsonl`

## Important Notes

- **Pull worker must be running** on your Mac
- **Folder must be allowlisted**: "MCP Inbox", "Work", or "Personal"
- **Each job is one JSON line** - no line breaks in the JSON
- **Jobs are processed every 15 seconds**

## Example

**User asks**: "Create a note titled 'Meeting Notes' with body 'Discussed project timeline'"

**ChatGPT should**:
1. Run the sign_job command with those parameters
2. Get the JSON output
3. Tell user: "I've generated a job. Please add this line to your Gist's queue.jsonl file: [paste JSON]"
4. Confirm: "The note will be created in Apple Notes within 15-30 seconds."

## Troubleshooting

- **Job not processing?** Check that pull worker is running
- **Error in results.jsonl?** Check the error message
- **Folder denied?** Use "MCP Inbox" which is always allowed
