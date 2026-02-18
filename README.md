# Jiminny MCP Server for Cursor

Access your Jiminny sales call transcripts, summaries, and action items directly from Cursor.

## What You Can Do

Ask Cursor things like:
- "List my recent Jiminny conversations"
- "Get the transcript for the call with Luc Bernard"
- "Summarize last week's SoV growth meeting"
- "Find calls where pricing was discussed"

## Setup (3 minutes)

### 1. Clone this repo

```bash
git clone https://github.com/fzheng0222/jiminny-mcp.git
```

### 2. Open in Cursor and ask it to set up

Open the cloned folder in Cursor, then in chat type:

> **"Help me set up this MCP server"**

Cursor will automatically:
- Install dependencies
- Walk you through getting your Jiminny token (with step-by-step instructions)
- Configure everything for you

### 3. Restart Cursor

Press **Cmd+Shift+P** → type **"Reload Window"** → hit Enter.

That's it! Open a new chat and try: *"List my recent Jiminny conversations"*

## Token Expired?

If you see a 401 error, your token needs refreshing. Just ask Cursor:

> **"Update my Jiminny token"**

It will walk you through getting a new one.

## Available Tools

| Tool | What it does |
|---|---|
| `jiminny_list_conversations` | Lists recorded calls (paginated, newest first) |
| `jiminny_get_transcript` | Full transcript with speaker labels and timestamps |
| `jiminny_get_summary` | AI-generated summary, action items, and key points |

## Troubleshooting

| Problem | Fix |
|---|---|
| "JIMINNY_TOKEN is not set" | Ask Cursor: "help me set up this MCP server" |
| 401 error | Token expired — ask Cursor: "update my Jiminny token" |
| 403 error | You don't have access to that conversation in Jiminny |
| Tools not showing | Restart Cursor (Cmd+Shift+P → "Reload Window") |
