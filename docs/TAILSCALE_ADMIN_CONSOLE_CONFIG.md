# Tailscale Admin Console Configuration

## Understanding the Architecture

The correct setup requires **two components**:

1. **Local Ingress Service** (Python/FastAPI)
   - Listens on `127.0.0.1:8443` (localhost only)
   - Handles HTTP requests and enqueues note jobs

2. **Tailscale Serve** (Forwarder)
   - Listens on Tailnet IP/port 8443
   - Forwards requests to `http://127.0.0.1:8443`

## The Problem

If you configured Tailscale serve in the admin console JSON config to "listen on port 8443", it might be:
- Trying to serve content directly (not forwarding)
- Pointing to the wrong backend URL
- Conflicting with the local service

## Solution: Use CLI Command (Recommended)

The CLI command overrides the admin console config and ensures correct forwarding:

```bash
# Reset any existing config
sudo /Applications/Tailscale.app/Contents/MacOS/tailscale serve reset

# Set up forwarding (this overrides admin console config)
sudo /Applications/Tailscale.app/Contents/MacOS/tailscale serve --bg --http=8443 http://127.0.0.1:8443

# Verify
/Applications/Tailscale.app/Contents/MacOS/tailscale serve status
```

## Admin Console JSON Config (Alternative)

If you prefer to use the admin console, the JSON config should look like:

```json
{
  "TCP": {
    "8443": {
      "HTTPS": false,
      "Handlers": {
        "HTTP": "http://127.0.0.1:8443"
      }
    }
  }
}
```

**Important:** The config must forward to `http://127.0.0.1:8443`, not listen directly.

## Verify Correct Setup

1. **Check local service is running:**
   ```bash
   curl http://127.0.0.1:8443/health
   # Should return: {"status":"ok"}
   ```

2. **Check Tailscale serve status:**
   ```bash
   /Applications/Tailscale.app/Contents/MacOS/tailscale serve status
   # Should show: http=8443 -> http://127.0.0.1:8443
   ```

3. **Test via Tailnet:**
   ```bash
   curl http://taila02178.ts.net:8443/health
   # Should return: {"status":"ok"}
   ```

## Troubleshooting

### Port Conflict

If you get "address already in use":
1. The local service must be running on `127.0.0.1:8443`
2. Tailscale serve should forward to it, not listen on the same port directly

### 404 from Tailscale

If you get 404 when accessing via Tailnet:
1. Verify local service works: `curl http://127.0.0.1:8443/health`
2. Check Tailscale serve is forwarding: `tailscale serve status`
3. Restart Tailscale serve with the CLI command above

### Admin Console vs CLI

- **CLI command** (`tailscale serve`) takes precedence over admin console config
- If you use CLI, it will override the admin console settings
- For this setup, **CLI is recommended** because it's explicit and easier to verify
- **One-time setup**: Once you run the CLI command, it persists until you reset it or change it
- **No need to update admin console JSON**: The CLI command overrides it, so you don't need to change the admin console config
- If you prefer admin console management, you can use `tailscale serve get-config` to export the current config, then use `set-config` to apply it via admin console
