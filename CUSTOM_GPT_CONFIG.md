# Custom GPT Configuration for Notes Creation

This guide provides the exact configuration needed to create a Custom GPT in ChatGPT that can create notes automatically.

**Purpose:** This GPT is optimized for fast capture into Apple Notes, not general chat. It automatically creates notes when you want to save, capture, remember, log, or note information.

## Prerequisites

✅ Tailscale Funnel is enabled and accessible (get your URL with: `tailscale funnel status`)  
✅ Ingress service is running  
✅ You have your `NOTES_MCP_INGRESS_KEY` from `start_worker.sh`

## Step 1: Create the Custom GPT

1. Go to: https://chatgpt.com/gpts/editor (or https://chat.openai.com/gpts as alternative)
2. Click **"Create"** button
3. You'll see a GPT builder interface

## Step 2: Configure Basic Settings

### Name
```
My Notes Assistant
```

### Description
```
My personal assistant that can create notes in Apple Notes automatically. Just tell me what note to create and I'll handle it.
```

### Instructions
```
You are an assistant that creates notes in Apple Notes using the create_note action.

Trigger behavior: When user intent is to save, capture, remember, log, or note information, automatically call create_note.

Rules:
- Always supply a concise descriptive title and clear structured body
- Folder selection rules:
  * Work / engineering / Red Hat / OpenShift / meetings -> "RedHat"
  * Personal life / health / travel / hobbies -> "Personal"
  * Anything unclear or unspecified -> "MCP Inbox"
  * Never invent folder names; only use these 3 allowed values: "MCP Inbox", "RedHat", "Personal"
- If required information (title or body) is missing or ambiguous, ask ONE clarifying question maximum
- After a successful API call (202 response), confirm: "Note queued successfully. It will appear in Apple Notes within 60 seconds."
- If API returns non-202 status, surface the error message and suggest checking /health endpoint and funnel/worker logs

HTML formatting (browser-based Custom GPT): You may send HTML in the body field for rich formatting. If the body starts with "<" and contains ">", the API treats it as HTML and Apple Notes will render it (bold, italic, lists, links, colors, tables, etc.). Use plain text when the user does not ask for formatting. Supported: <strong>, <em>, <u>, <s>, <p>, <h1>-<h6>, <ul>/<ol>/<li>, <a href="...">, <table>, <code>, <pre>, <hr>, <span style="...">, font-size/color/background-color. Avoid <br> (use separate <p> tags for line breaks). Blockquotes (<blockquote>) are not supported.

Tags: You may send an optional "tags" array (e.g. ["work", "meeting"]). Tags are appended to the note as hashtags (#work #meeting) so the user can search by #tagname in Apple Notes. Use tags when the user mentions categories or wants to find the note later by topic.
```

## Step 3: Add Action (API Integration)

1. Click **"Add Action"** or **"Create new action"**
2. You'll see an interface to configure the API

### Action Configuration

**Name:** `create_note`

**Description:** `Creates a note in Apple Notes via the Tailscale API`

### OpenAPI Schema

**Option 1: Use the working example file (recommended)**

1. Copy `gpt_action.json.example` from this repository
2. Replace `YOUR-MACHINE-NAME.tailscale.ts.net` with your actual Tailscale Funnel URL (get it with: `tailscale funnel status`)
3. Update the `folder` enum values (line 36) to match your `NOTES_MCP_ALLOWED_FOLDERS` from `start_worker.sh` (e.g., replace "Work" with your actual folder names)
4. Paste the modified JSON into ChatGPT's schema editor

**Option 2: Paste from openapi-schema.json**

Copy the contents of `openapi-schema.json` in this repository and paste it into the schema editor (remember to update the server URL).

**Option 3: Paste directly (minimal version)**

Paste this entire schema into the schema editor:

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "Notes MCP API",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "https://YOUR-MACHINE-NAME.tailscale.ts.net"
    }
  ],
  "paths": {
    "/notes": {
      "post": {
        "operationId": "create_note",
        "summary": "Create a note in Apple Notes",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "required": ["title", "body"],
                "additionalProperties": false,
                "properties": {
                  "title": {
                    "type": "string",
                    "description": "Note title (max 200 characters)",
                    "maxLength": 200
                  },
                  "body": {
                    "type": "string",
                    "description": "Note content: plain text or HTML. If body starts with '<' and contains tags, rendered as HTML (bold, lists, links, etc.). Otherwise plain text with line breaks. See doc for HTML formatting.",
                    "maxLength": 50000
                  },
                  "folder": {
                    "type": "string",
                    "enum": ["MCP Inbox", "RedHat", "Personal"],
                    "default": "MCP Inbox",
                    "description": "Folder name"
                  },
                  "account": {
                    "type": "string",
                    "enum": ["iCloud", "On My Mac"],
                    "default": "iCloud",
                    "description": "Account name"
                  },
                  "tags": {
                    "type": "array",
                    "items": { "type": "string" },
                    "maxItems": 20,
                    "description": "Optional tags; appended as hashtags so notes can be searched by #tagname in Apple Notes"
                  }
                }
              },
              "example": {
                "title": "Meeting Notes - Project Review",
                "body": "Discussed project timeline and deliverables.",
                "folder": "RedHat",
                "account": "iCloud"
              }
            }
          }
        },
        "responses": {
          "202": {
            "description": "Note queued successfully",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "status": {
                      "type": "string"
                    },
                    "job_id": {
                      "type": "string"
                    },
                    "message": {
                      "type": "string"
                    },
                    "folder": {
                      "type": "string"
                    },
                    "account": {
                      "type": "string"
                    }
                  }
                },
                "example": {
                  "status": "queued",
                  "job_id": "abc123def456",
                  "message": "Note creation job enqueued successfully",
                  "folder": "RedHat",
                  "account": "iCloud"
                }
              }
            }
          }
        },
        "security": [
          {
            "ApiKeyAuth": []
          }
        ]
      }
    }
  },
  "components": {
    "securitySchemes": {
      "ApiKeyAuth": {
        "type": "apiKey",
        "in": "header",
        "name": "X-Notes-MCP-Key"
      }
    },
    "schemas": {}
  }
}
```

**Troubleshooting:** If you get a parsing error, try:
1. Make sure you're copying the entire JSON block (from `{` to `}`)
2. Remove any extra whitespace or line breaks
3. Use the `openapi-schema.json` file from the repository instead

### Authentication

1. Click **"Add authentication"** or find the authentication section
2. Select **"API Key"** as the authentication type
3. When prompted for auth type, choose **"Custom"** (not Basic or Bearer)
4. **Important:** The header name `X-Notes-MCP-Key` is already defined in the OpenAPI schema (in the `components.securitySchemes` section), so ChatGPT will use it automatically. You don't need to set it manually.
5. In the **"API Key"** or **"Key"** field (the only field you should see), enter your `NOTES_MCP_INGRESS_KEY` value from `start_worker.sh`

**How it works:** The OpenAPI schema specifies that the API key goes in a header named `X-Notes-MCP-Key`. When you paste the schema, ChatGPT reads this configuration and automatically uses the correct header name. You only need to provide the key value.

## Step 4: Test the Action

1. Click **"Test"** or save the GPT
2. In a chat with your Custom GPT, try:
   ```
   Create a test note titled "GPT Test" with body "This is a test from ChatGPT"
   ```
3. The GPT should automatically call the API and create the note
4. Check Apple Notes within 60 seconds to verify the note was created

**Note:** If the API returns a non-202 status code, the GPT will surface the error. Check the `/health` endpoint and review funnel/worker logs for troubleshooting.

**Optional Future Improvement:** Consider switching the endpoint path to `/v1/notes` for future API versioning. This would require updating the ingress service and is a future refactor, not needed for initial setup.

## Step 5: Save and Use

1. Click **"Save"** in the top right
2. Choose visibility:
   - **"Only me"** - Private, only you can use it
   - **"Anyone with a link"** - Shareable link
   - **"Public"** - Listed in GPT store (not recommended for personal use)
3. Click **"Confirm"**

## Using HTML for rich formatting (browser-based Custom GPT)

The API accepts **HTML in the note body**. When the body starts with `<` and contains `>`, it is rendered as rich text in Apple Notes.

### Enabling HTML in your Custom GPT

The OpenAPI schema already describes that `body` can be plain text or HTML. Add this to your GPT **Instructions** (see Step 2) so the model uses HTML when appropriate:

- *"You may send HTML in the body field for rich formatting. If the body starts with '<' and contains '>', the API treats it as HTML. Use <strong>, <em>, <ul>/<li>, <a href>, <table>, <code>, <pre>, <hr>, headings, and inline styles for colors/fonts. Use separate <p> tags for line breaks (avoid <br>). Blockquotes are not supported."*

### What works in Apple Notes

| Formatting | HTML | Works |
|------------|------|-------|
| Bold, italic, underline, strikethrough | `<strong>`, `<em>`, `<u>`, `<s>` | ✅ |
| Font sizes, families, colors | `style="font-size:18px"`, `color:red`, etc. | ✅ |
| Text alignment | `text-align:center`, `right`, `justify` | ✅ |
| Bullet and numbered lists | `<ul>`, `<ol>`, `<li>` (including nested) | ✅ |
| Links | `<a href="https://...">text</a>` | ✅ |
| Tables | `<table>`, `<tr>`, `<th>`, `<td>` | ✅ |
| Code | `<code>`, `<pre>` | ✅ |
| Horizontal rules | `<hr>` | ✅ |
| Headings | `<h1>`–`<h6>` | ✅ |
| Line breaks | Use separate `<p>...</p>` per line | ✅ |
| Blockquotes | `<blockquote>` | ❌ |

Full details: see `APPLE_NOTES_FORMATTING_SUPPORT.md`.

### Example: formatted note via Custom GPT

User: *"Save a note titled 'Meeting recap' with a bullet list of action items and bold the names."*

The GPT can send a body like:

```html
<p><strong>Action items</strong></p>
<ul>
<li>Alice: send design mockups by Friday</li>
<li>Bob: update API docs</li>
<li>Carol: schedule follow-up</li>
</ul>
```

The note will appear in Apple Notes with bold heading and bullet list.

---

## Usage

Once configured, you can use your Custom GPT like this:

- "Create a note about the meeting with John tomorrow"
- "Save this to my RedHat folder: [content]"
- "Make a note titled 'Project Ideas' with the following: [ideas]"
- "Create a note with a bullet list and bold the key points" (GPT can use HTML body)

The GPT will automatically:
1. Format your request into the API call (plain text or HTML body when appropriate)
2. Include the authentication key
3. Call the API
4. Confirm when the note is created

## Troubleshooting

### "ClientResponseError" or API call fails

If ChatGPT reports a `ClientResponseError` when calling the API:

1. **Verify authentication is configured correctly:**
   - In GPT builder → Actions → Authentication
   - Type: API Key
   - Auth Type: Custom
   - API Key value: Your `NOTES_MCP_INGRESS_KEY` from `start_worker.sh`
   - The header name `X-Notes-MCP-Key` should be read from the OpenAPI schema automatically

2. **Test the API directly:**
   ```bash
   curl -X POST https://YOUR-MACHINE-NAME.tailscale.ts.net/notes \
     -H "Content-Type: application/json" \
     -H "X-Notes-MCP-Key: YOUR_INGRESS_KEY_HERE" \
     -d '{"title":"Test","body":"Test","folder":"MCP Inbox","account":"iCloud"}'
   ```
   If this works but ChatGPT doesn't, it's an authentication configuration issue.

3. **Check ingress service logs:**
   ```bash
   tail -f ~/Library/Logs/notes-mcp/ingress.log
   ```
   Look for incoming requests when ChatGPT tries to call the API.

4. **Verify the service is running:**
   ```bash
   curl https://YOUR-MACHINE-NAME.tailscale.ts.net/health
   ```
   Should return: `{"status":"ok","service":"notes-mcp-ingress"}`

See `CUSTOM_GPT_TROUBLESHOOTING.md` for detailed debugging steps.

### "Invalid or missing X-Notes-MCP-Key header"
- Verify the key value matches your `NOTES_MCP_INGRESS_KEY` from `start_worker.sh`
- Check that it's set as a header, not in the request body

### "Folder 'X' is not in allowed folders list"
- Only these folders are allowed: "MCP Inbox", "RedHat", "Personal"
- Make sure the folder name matches exactly (case-sensitive)

### "Failed to connect"
- Verify Tailscale Funnel is running: `/Applications/Tailscale.app/Contents/MacOS/tailscale funnel status`
- Check that the ingress service is running: `curl https://YOUR-MACHINE-NAME.tailscale.ts.net/health`

### Note not appearing
- Wait up to 60 seconds (worker polls every minute)
- Check that the pull worker is running: `launchctl list | grep notes-mcp`
- Check worker logs: `tail -f ~/Library/Logs/notes-mcp/worker.log`

## Security Notes

- The ingress key is sensitive - don't share it publicly
- The Custom GPT is configured with the key, so anyone with access to your GPT can create notes
- Keep the GPT private ("Only me") for security
- The API is rate-limited (30 requests/minute per IP)
