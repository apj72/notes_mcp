# Setting Up Pull Worker as macOS Background Service

This guide explains how to set up the notes-mcp pull worker to run automatically in the background and restart on reboot.

## Overview

The pull worker can run as a macOS launchd service, which means:
- ✅ Runs in the background (no terminal window needed)
- ✅ Starts automatically on login/reboot
- ✅ Restarts automatically if it crashes
- ✅ Logs to files for easy monitoring

## Prerequisites

1. **`start_worker.sh` is configured** with your actual tokens
2. **`start_worker.sh` is executable**: `chmod +x start_worker.sh`

## Quick Setup (Automated)

### Step 1: Stop Any Running Worker

If you have the worker running in a terminal, stop it first:
- Press `Ctrl+C` in the terminal window

### Step 2: Run Setup Script

```bash
cd /Users/ajoyce/git-repos/notes_mcp
./setup_service.sh
```

This script will:
- Make `start_worker.sh` executable
- Copy the plist file to `~/Library/LaunchAgents/`
- Load and start the service
- Verify it's running

### Step 3: Verify It's Working

```bash
# Check service status
launchctl list | grep notes-mcp

# View output log
tail -f /tmp/notes-mcp-worker.out

# View error log (if any)
tail -f /tmp/notes-mcp-worker.err
```

You should see output like:
```
Worker started. Polling every 15 seconds.
Gist ID: YOUR_GIST_ID
...
```

## Manual Setup

If you prefer to set it up manually:

### Step 1: Copy the Plist File

```bash
cp com.notes-mcp.worker.plist ~/Library/LaunchAgents/
```

### Step 2: Load the Service

```bash
launchctl load ~/Library/LaunchAgents/com.notes-mcp.worker.plist
```

### Step 3: Start the Service

```bash
launchctl start com.notes-mcp.worker
```

## Managing the Service

### Check Service Status

```bash
launchctl list | grep notes-mcp
```

If the service is running, you'll see:
```
-   0    com.notes-mcp.worker
```

The first number is the process ID (PID). If it shows `-` and `0`, the service is loaded but may not be running.

### Start the Service

```bash
launchctl start com.notes-mcp.worker
```

### Stop the Service

```bash
launchctl stop com.notes-mcp.worker
```

**Note**: Stopping the service will prevent it from processing jobs, but it will automatically restart when you log in or reboot (if `KeepAlive` is enabled).

### Restart the Service

To restart the service (useful after making changes to `start_worker.sh`):

```bash
launchctl stop com.notes-mcp.worker
launchctl start com.notes-mcp.worker
```

Or unload and reload:

```bash
launchctl unload ~/Library/LaunchAgents/com.notes-mcp.worker.plist
launchctl load ~/Library/LaunchAgents/com.notes-mcp.worker.plist
```

### Unload (Disable) the Service

To completely disable the service (it won't start on reboot):

```bash
launchctl unload ~/Library/LaunchAgents/com.notes-mcp.worker.plist
```

To re-enable it later:

```bash
launchctl load ~/Library/LaunchAgents/com.notes-mcp.worker.plist
```

### Remove the Service

To permanently remove the service:

```bash
# Unload first
launchctl unload ~/Library/LaunchAgents/com.notes-mcp.worker.plist

# Remove the plist file
rm ~/Library/LaunchAgents/com.notes-mcp.worker.plist
```

## Monitoring the Service

### View Output Logs

The service writes output to:
```bash
tail -f /tmp/notes-mcp-worker.out
```

This shows:
- Worker startup messages
- Job processing status
- Polling activity

### View Error Logs

Check for errors:
```bash
tail -f /tmp/notes-mcp-worker.err
```

### Check if Process is Running

```bash
ps aux | grep pull_worker
```

You should see a Python process running `notes_mcp.pull_worker`.

### View System Logs

For more detailed system logs:
```bash
log show --predicate 'process == "notes-mcp"' --last 1h
```

## Troubleshooting

### Service Not Starting

1. **Check error log:**
   ```bash
   cat /tmp/notes-mcp-worker.err
   ```

2. **Verify start_worker.sh is executable:**
   ```bash
   ls -l start_worker.sh
   chmod +x start_worker.sh
   ```

3. **Test start_worker.sh manually:**
   ```bash
   ./start_worker.sh
   ```
   If it works manually but not as a service, check the error log.

4. **Verify environment variables:**
   Make sure all required variables are set in `start_worker.sh`:
   - `NOTES_QUEUE_GIST_ID`
   - `GITHUB_TOKEN`
   - `NOTES_MCP_TOKEN`

### Service Stops Unexpectedly

1. **Check error logs:**
   ```bash
   tail -20 /tmp/notes-mcp-worker.err
   ```

2. **Check if it's restarting:**
   The `KeepAlive` key ensures the service restarts automatically. Check the logs to see if it's restarting repeatedly.

3. **Check system resources:**
   ```bash
   ps aux | grep pull_worker
   ```

### Service Not Processing Jobs

1. **Verify service is running:**
   ```bash
   launchctl list | grep notes-mcp
   ps aux | grep pull_worker
   ```

2. **Check output log for activity:**
   ```bash
   tail -f /tmp/notes-mcp-worker.out
   ```

3. **Test with a job:**
   ```bash
   python3 -m notes_mcp.sign_job --title "Test" --body "Test" | python3 -m notes_mcp.enqueue_job
   ```

4. **Check your Gist:**
   - Verify `queue.jsonl` has valid jobs
   - Check `results.jsonl` for processing results

### Service Not Starting on Reboot

1. **Verify plist is in correct location:**
   ```bash
   ls -l ~/Library/LaunchAgents/com.notes-mcp.worker.plist
   ```

2. **Check if service is loaded:**
   ```bash
   launchctl list | grep notes-mcp
   ```

3. **Reload the service:**
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.notes-mcp.worker.plist
   launchctl load ~/Library/LaunchAgents/com.notes-mcp.worker.plist
   ```

## Service Configuration

The service is configured via `com.notes-mcp.worker.plist`. Key settings:

- **`RunAtLoad`**: `true` - Starts automatically when loaded
- **`KeepAlive`**: `true` - Restarts automatically if it crashes
- **`StandardOutPath`**: `/tmp/notes-mcp-worker.out` - Output log location
- **`StandardErrorPath`**: `/tmp/notes-mcp-worker.err` - Error log location

## Updating the Service

If you make changes to `start_worker.sh`:

1. **Edit the file:**
   ```bash
   nano start_worker.sh  # or use your preferred editor
   ```

2. **Restart the service:**
   ```bash
   launchctl stop com.notes-mcp.worker
   launchctl start com.notes-mcp.worker
   ```

3. **Verify it's working:**
   ```bash
   tail -f /tmp/notes-mcp-worker.out
   ```

## Quick Reference

| Action | Command |
|--------|---------|
| **Setup** | `./setup_service.sh` |
| **Check status** | `launchctl list \| grep notes-mcp` |
| **Start** | `launchctl start com.notes-mcp.worker` |
| **Stop** | `launchctl stop com.notes-mcp.worker` |
| **Restart** | `launchctl stop com.notes-mcp.worker && launchctl start com.notes-mcp.worker` |
| **View logs** | `tail -f /tmp/notes-mcp-worker.out` |
| **View errors** | `tail -f /tmp/notes-mcp-worker.err` |
| **Unload** | `launchctl unload ~/Library/LaunchAgents/com.notes-mcp.worker.plist` |
| **Load** | `launchctl load ~/Library/LaunchAgents/com.notes-mcp.worker.plist` |

## Notes

- The service runs as your user (not root)
- Logs are written to `/tmp/` and may be cleared on reboot
- The service will automatically start on login/reboot
- If the service crashes, it will automatically restart (due to `KeepAlive`)
- To permanently disable, unload the service

## Security

- The plist file does NOT contain your tokens (they're in `start_worker.sh`)
- `start_worker.sh` is in `.gitignore` and won't be committed
- The service runs with your user permissions
- All environment variables are set by `start_worker.sh`
