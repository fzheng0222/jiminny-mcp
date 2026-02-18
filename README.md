# Jiminny MCP Server for Cursor

Access your Jiminny sales call transcripts, summaries, and action items directly from Cursor.

## What You Can Do

Ask Cursor things like:
- "List my recent Jiminny conversations"
- "Get the transcript for the call with Luc Bernard"
- "Summarize last week's SoV growth meeting"
- "Find calls where pricing was discussed"

## Quick Setup (< 5 minutes)

### 1. Get your Jiminny token

1. Open [app.jiminny.com](https://app.jiminny.com) in Chrome and log in
2. Press **F12** (or **Cmd+Option+I** on Mac) to open Developer Tools
3. Click the **Network** tab
4. Refresh the page (**Cmd+R** or **F5**)
5. Click any request in the list (e.g., one starting with `on-demand`)
6. Scroll down to **Request Headers**
7. Find the `Authorization` header — it looks like `Bearer eyJhbGci...`
8. Copy everything **after** `Bearer ` (the long string starting with `eyJ`)

> **Tip:** The token expires after a while. If you get a 401 error, repeat these steps to get a fresh token.

### 2. Install the server

**Option A — Automatic setup (recommended):**

```bash
git clone https://github.com/fzheng0222/jiminny-mcp.git
cd jiminny-mcp
bash setup.sh
```

**Option B — Manual setup:**

1. Clone this repo somewhere on your machine:
   ```bash
   git clone https://github.com/fzheng0222/jiminny-mcp.git ~/.jiminny-mcp
   cd ~/.jiminny-mcp
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   uv venv .venv
   uv pip install -e .
   ```
   (Don't have `uv`? Install it: `curl -LsSf https://astral.sh/uv/install.sh | sh`)

3. Add to Cursor — open (or create) `~/.cursor/mcp.json` and add:
   ```json
   {
     "mcpServers": {
       "jiminny": {
         "command": "/Users/YOUR_USERNAME/.jiminny-mcp/.venv/bin/python",
         "args": ["/Users/YOUR_USERNAME/.jiminny-mcp/src/server.py"],
         "env": {
           "JIMINNY_TOKEN": "paste-your-token-here"
         }
       }
     }
   }
   ```
   Replace `YOUR_USERNAME` with your macOS username and paste your token.

4. **Restart Cursor** (Cmd+Shift+P → "Reload Window")

### 3. Verify it works

Open a new Cursor chat and type:

> List my recent Jiminny conversations

You should see a list of your team's recorded calls.

## Updating Your Token

When your token expires (you'll see a 401 error), either:

- **Re-run the setup:** `cd ~/.jiminny-mcp && bash setup.sh`
- **Edit directly:** Open `~/.cursor/mcp.json`, replace the token value, and reload Cursor

## Available Tools

| Tool | What it does |
|---|---|
| `jiminny_list_conversations` | Lists recorded calls (paginated, newest first) |
| `jiminny_get_transcript` | Gets the full transcript of a call with speaker labels and timestamps |
| `jiminny_get_summary` | Gets AI-generated summary, action items, and key points |

## Troubleshooting

| Problem | Fix |
|---|---|
| "JIMINNY_TOKEN is not set" | Check your `~/.cursor/mcp.json` has the token |
| 401 error | Token expired — get a new one from Jiminny DevTools |
| 403 error | You don't have access to that conversation |
| Tools not showing in Cursor | Restart Cursor (Cmd+Shift+P → "Reload Window") |
