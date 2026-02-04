# Tags in Notes

## How tags work

Apple Notes does **not** expose tags via AppleScript. The Notes app has a tags feature in the UI, but there is no scriptable API to set or read tags when creating notes.

**Workaround:** Notes MCP appends tags to the note **body as hashtags** (e.g. `#work #meeting`). In Apple Notes you can then:

- **Search** by `#tagname` in the Notes search field
- Use **Smart Folders** or filters that match hashtags in the body

So tags are stored as visible hashtags at the end of the note content. They are part of the note text, not a separate Notes “tag” field.

## API usage

### Optional `tags` parameter

- **Ingress / Custom GPT:** Send `"tags": ["work", "meeting"]` in the JSON body.
- **MCP tool:** Pass `"tags": ["work", "meeting"]` in the `notes.create` arguments.
- **CLI:** `python3 -m notes_mcp.sign_job --title "Note" --body "Content" --tags work meeting`

### Normalization

- Each tag is normalized to a hashtag: leading `#` is optional, spaces become `_`, max 50 characters per tag.
- Up to 20 tags per note; duplicates are removed.
- They are appended as a single line at the end of the note body, e.g. `<p>#work #meeting</p>` in HTML or the equivalent in plain text.

### Example

Request:

```json
{
  "title": "Standup notes",
  "body": "Discussed sprint goals.",
  "folder": "MCP Inbox",
  "tags": ["work", "standup", "sprint"]
}
```

The note body in Apple Notes will end with:

```
#work #standup #sprint
```

You can then search in Notes for `#standup` or `#sprint` to find this note.

## Summary

| Feature              | Supported |
|----------------------|-----------|
| Add tags via API     | ✅ As hashtags in body |
| Search by #tagname   | ✅ In Notes search |
| Native Notes “tags”  | ❌ Not scriptable |
