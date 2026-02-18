#!/usr/bin/env bash
set -euo pipefail

# Jiminny MCP Server — One-liner setup for Cursor
# Usage: curl -sL <raw-github-url>/setup.sh | bash

REPO_URL="https://github.com/fzheng0222/jiminny-mcp.git"
INSTALL_DIR="$HOME/.jiminny-mcp"
MCP_CONFIG="$HOME/.cursor/mcp.json"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   Jiminny MCP Server — Setup for Cursor      ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# --- Step 1: Check for Python 3.10+ ---
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
    if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
        echo "❌ Python 3.10+ required (found $PY_VERSION)"
        echo "   Install from: https://www.python.org/downloads/"
        exit 1
    fi
    echo "✅ Python $PY_VERSION found"
else
    echo "❌ Python 3 not found. Install from: https://www.python.org/downloads/"
    exit 1
fi

# --- Step 2: Install uv if not present ---
if ! command -v uv &>/dev/null; then
    echo "📦 Installing uv (Python package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo "✅ uv installed"
else
    echo "✅ uv already installed"
fi

# --- Step 3: Clone or update the repo ---
if [ -d "$INSTALL_DIR" ]; then
    echo "📁 Updating existing installation..."
    cd "$INSTALL_DIR"
    git pull --quiet
else
    echo "📥 Downloading Jiminny MCP server..."
    git clone --quiet "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# --- Step 4: Install dependencies ---
echo "📦 Installing dependencies..."
cd "$INSTALL_DIR"
uv venv --quiet .venv
uv pip install --quiet -e .
echo "✅ Dependencies installed"

# --- Step 5: Get Jiminny token ---
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🔑 Now we need your Jiminny token."
echo ""
echo "  1. Open https://app.jiminny.com in Chrome"
echo "  2. Press F12 (or Cmd+Opt+I) to open DevTools"
echo "  3. Click the 'Network' tab"
echo "  4. Refresh the page (Cmd+R / F5)"
echo "  5. Click any request in the list"
echo "  6. Under 'Request Headers', find 'Authorization'"
echo "  7. Copy everything AFTER 'Bearer '"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -rp "Paste your Jiminny token here: " JIMINNY_TOKEN

if [ -z "$JIMINNY_TOKEN" ]; then
    echo "❌ No token provided. You can set it later in: $MCP_CONFIG"
    JIMINNY_TOKEN="PASTE_YOUR_TOKEN_HERE"
fi

# --- Step 6: Configure Cursor MCP ---
echo ""
echo "⚙️  Configuring Cursor..."

VENV_PYTHON="$INSTALL_DIR/.venv/bin/python"
SERVER_SCRIPT="$INSTALL_DIR/src/server.py"

mkdir -p "$(dirname "$MCP_CONFIG")"

if [ -f "$MCP_CONFIG" ]; then
    EXISTING=$(cat "$MCP_CONFIG")
else
    EXISTING="{}"
fi

# Use python to safely merge into existing mcp.json
python3 -c "
import json, sys

existing = json.loads('''$EXISTING''')
if 'mcpServers' not in existing:
    existing['mcpServers'] = {}

existing['mcpServers']['jiminny'] = {
    'command': '$VENV_PYTHON',
    'args': ['$SERVER_SCRIPT'],
    'env': {
        'JIMINNY_TOKEN': '$JIMINNY_TOKEN'
    }
}

with open('$MCP_CONFIG', 'w') as f:
    json.dump(existing, f, indent=2)
"

echo "✅ Cursor configured"

# --- Done! ---
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   ✅ Setup complete!                         ║"
echo "║                                              ║"
echo "║   Restart Cursor, then ask:                  ║"
echo "║   'List my recent Jiminny conversations'     ║"
echo "║                                              ║"
echo "║   Token expired? Re-run this script or       ║"
echo "║   edit: ~/.cursor/mcp.json                   ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
