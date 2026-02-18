#!/usr/bin/env python3
"""
MCP Server for Jiminny conversation intelligence platform.

Provides tools to list sales conversations, retrieve transcripts,
and get AI-generated summaries from Jiminny.
"""

import json
import os
from typing import Optional, Any

import httpx
from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
API_BASE_URL = "https://app.jiminny.com/api/v1"
CHARACTER_LIMIT = 25_000
DEFAULT_PAGE_SIZE = 25

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
mcp = FastMCP("jiminny_mcp")

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _get_token() -> str:
    """Return the Jiminny Bearer token from the environment."""
    token = os.environ.get("JIMINNY_TOKEN", "")
    if not token:
        raise RuntimeError(
            "JIMINNY_TOKEN environment variable is not set. "
            "Get your token from Jiminny browser DevTools: "
            "Network tab > any API request > Authorization header (copy the value after 'Bearer ')."
        )
    return token


def _auth_headers() -> dict[str, str]:
    """Return common request headers with auth."""
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


async def _api_get(path: str, params: Optional[dict[str, Any]] = None) -> Any:
    """Make an authenticated GET request to the Jiminny API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{API_BASE_URL}/{path}",
            headers=_auth_headers(),
            params=params,
        )
        response.raise_for_status()
        return response.json()


def _format_seconds(seconds: float) -> str:
    """Convert seconds to MM:SS format."""
    mins, secs = divmod(int(seconds), 60)
    return f"{mins}:{secs:02d}"


async def _get_participant_names(conversation_id: str) -> dict[str, str]:
    """Try to build a participantId -> display name mapping."""
    mapping: dict[str, str] = {}
    try:
        data = await _api_get(f"activity/{conversation_id}/participants")
        participants = data if isinstance(data, list) else data.get("participants", data.get("data", data.get("results", [])))
        if isinstance(participants, list):
            for p in participants:
                if isinstance(p, dict):
                    pid = p.get("id") or p.get("participantId") or ""
                    name = p.get("name") or p.get("displayName") or p.get("email") or ""
                    if pid and name:
                        mapping[pid] = name
    except Exception:
        pass
    return mapping


def _handle_error(e: Exception) -> str:
    """Format API errors into helpful messages."""
    if isinstance(e, RuntimeError) and "JIMINNY_TOKEN" in str(e):
        return str(e)
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        if status == 401:
            return (
                "Error: Authentication failed (401). Your token may have expired. "
                "Go to Jiminny in your browser, open DevTools > Network tab, "
                "refresh the page, and copy the new Bearer token."
            )
        if status == 403:
            return "Error: Permission denied (403). You don't have access to this resource."
        if status == 404:
            return "Error: Not found (404). Check that the conversation ID is correct."
        if status == 429:
            return "Error: Rate limit exceeded (429). Wait a moment and try again."
        return f"Error: Jiminny API returned status {status}."
    if isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out. Try again."
    return f"Error: {type(e).__name__}: {e}"


def _truncate(text: str) -> str:
    """Truncate text to CHARACTER_LIMIT with a warning."""
    if len(text) <= CHARACTER_LIMIT:
        return text
    return text[:CHARACTER_LIMIT] + "\n\n... [truncated — response exceeded character limit]"

# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def _format_conversation_list(data: dict[str, Any]) -> str:
    """Format the on-demand/search response as readable markdown."""
    results = data.get("results", [])
    pagination = data.get("pagination", {})
    total = pagination.get("total", len(results))
    current_page = pagination.get("current", 1)
    next_page = pagination.get("next", None)

    lines = [
        f"# Jiminny Conversations (page {current_page}, {total} total)",
        "",
    ]

    if not results:
        lines.append("No conversations found.")
        return "\n".join(lines)

    for r in results:
        title = r.get("title", "Untitled")
        conv_id = r.get("id", "")
        duration = r.get("durationForHumans", "")
        start = r.get("actualStartTime", "")[:10] if r.get("actualStartTime") else ""
        organizer = r.get("organizer", {}).get("name", "") if isinstance(r.get("organizer"), dict) else ""
        prospect_name = r.get("prospect", {}).get("name", "") if isinstance(r.get("prospect"), dict) else ""
        category = r.get("category", {}).get("name", "") if isinstance(r.get("category"), dict) else ""
        provider = r.get("provider", "")
        is_summarized = r.get("isSummarized", False)
        has_transcript = r.get("hasTranscription", False)
        status = r.get("status", "")

        lines.append(f"## {title}")
        lines.append(f"- **ID**: `{conv_id}`")
        if start:
            lines.append(f"- **Date**: {start}")
        if duration:
            lines.append(f"- **Duration**: {duration}")
        if organizer:
            lines.append(f"- **Host**: {organizer}")
        if prospect_name:
            lines.append(f"- **Contact**: {prospect_name}")
        if category:
            lines.append(f"- **Category**: {category}")
        if provider:
            lines.append(f"- **Provider**: {provider}")
        lines.append(f"- **Transcript**: {'Yes' if has_transcript else 'No'} | **Summary**: {'Yes' if is_summarized else 'No'}")
        if status:
            lines.append(f"- **Status**: {status}")
        lines.append("")

    if next_page:
        lines.append(f"_More results available — request page {next_page}._")

    return _truncate("\n".join(lines))

# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------

class ListConversationsInput(BaseModel):
    """Input for listing Jiminny conversations."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    page: int = Field(
        default=1,
        description="Page number to retrieve (default: 1). Each page has ~25 conversations.",
        ge=1,
    )


class ConversationIdInput(BaseModel):
    """Input requiring a single conversation ID."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    conversation_id: str = Field(
        ...,
        description="The Jiminny conversation UUID (e.g. 'ad0a10bc-90ce-44f3-baa4-2c7ce6d7104c'). Get IDs from jiminny_list_conversations.",
        min_length=1,
    )

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool(
    name="jiminny_list_conversations",
    annotations={
        "title": "List Jiminny Conversations",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def jiminny_list_conversations(params: ListConversationsInput) -> str:
    """List recorded sales conversations from Jiminny, newest first.

    Returns a paginated list of conversations with title, date, duration,
    host, contact, and conversation ID. Use the ID to fetch transcripts
    or summaries with the other tools.

    Args:
        params: Contains page number (default 1, ~25 results per page).

    Returns:
        Markdown-formatted list of conversations with metadata.
    """
    try:
        data = await _api_get("page/on-demand", params={"page": params.page})
        return _format_conversation_list(data)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="jiminny_get_transcript",
    annotations={
        "title": "Get Conversation Transcript",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def jiminny_get_transcript(params: ConversationIdInput) -> str:
    """Get the full transcript of a Jiminny conversation.

    Returns the complete text transcript of a recorded sales call,
    formatted as readable dialogue with speaker names and timestamps.

    Args:
        params: Contains the conversation UUID.

    Returns:
        The transcript as text/markdown, or an error message.
    """
    try:
        cid = params.conversation_id
        data = await _api_get(f"activity/{cid}/transcription")

        segments = data if isinstance(data, list) else (
            data.get("segments") or data.get("entries") or
            data.get("data") or data.get("results") or []
            if isinstance(data, dict) else []
        )

        if isinstance(data, dict) and not segments:
            for key in ("transcript", "text", "content", "transcription"):
                if key in data and isinstance(data[key], str):
                    return _truncate(f"# Transcript\n\n{data[key]}")

        if not isinstance(segments, list) or not segments:
            return _truncate(f"# Transcript\n\n{str(data)}")

        names = await _get_participant_names(cid)

        speaker_counter = 0
        auto_names: dict[str, str] = {}

        lines = ["# Transcript", ""]
        prev_speaker = None

        for seg in segments:
            if not isinstance(seg, dict):
                continue

            text = seg.get("transcript") or seg.get("text") or seg.get("content") or ""
            if not text.strip():
                continue

            pid = seg.get("participantId") or seg.get("speaker") or "unknown"
            start = seg.get("startsAt") or seg.get("startTime") or seg.get("start") or 0

            if pid in names:
                speaker = names[pid]
            elif pid in auto_names:
                speaker = auto_names[pid]
            else:
                speaker_counter += 1
                speaker = f"Speaker {speaker_counter}"
                auto_names[pid] = speaker

            timestamp = _format_seconds(float(start)) if start else ""

            if speaker != prev_speaker:
                lines.append(f"\n**{speaker}** [{timestamp}]:\n{text}")
                prev_speaker = speaker
            else:
                lines.append(text)

        if names:
            lines.insert(2, "_Participants: " + ", ".join(names.values()) + "_\n")
        elif auto_names:
            lines.insert(2, f"_Note: {len(auto_names)} speakers detected (names could not be resolved)_\n")

        return _truncate("\n".join(lines))

    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="jiminny_get_summary",
    annotations={
        "title": "Get Conversation Summary",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def jiminny_get_summary(params: ConversationIdInput) -> str:
    """Get the AI-generated summary, action items, and key points for a conversation.

    Fetches the transcription summary, action items, and key points
    for a Jiminny conversation and combines them into a single report.

    Args:
        params: Contains the conversation UUID.

    Returns:
        Markdown report with summary, action items, and key points.
    """
    cid = params.conversation_id
    lines = ["# Conversation Summary", ""]

    # Try multiple path patterns since the API may use different prefixes
    path_prefixes = [f"activity/{cid}", f"conference/{cid}"]

    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = _auth_headers()

        async def _try_get(suffix: str) -> tuple[int, Any, str]:
            """Try fetching a resource with fallback path prefixes. Returns (status, data, debug_info)."""
            attempts: list[str] = []
            for prefix in path_prefixes:
                url = f"{API_BASE_URL}/{prefix}/{suffix}"
                resp = await client.get(url, headers=headers)
                attempts.append(f"{url} → {resp.status_code}")
                if resp.status_code == 200:
                    return 200, resp.json(), f"OK: {url}"
            return resp.status_code, None, " | ".join(attempts)

        # --- Summary ---
        lines.append("## Summary")
        try:
            status, data, _ = await _try_get("transcription-summary")
            if status == 200 and data:
                summary_text = _extract_text(data, fallback_key="summary")
                lines.append(summary_text if summary_text else "_No summary available._")
            else:
                lines.append("_Summary not available via API. Use jiminny_get_transcript and ask for a summary in chat._")
        except Exception:
            lines.append("_Summary not available via API. Use jiminny_get_transcript and ask for a summary in chat._")
        lines.append("")

        # --- Action Items ---
        lines.append("## Action Items")
        try:
            status, data, _ = await _try_get("action-items")
            if status == 200 and data:
                action_items = _extract_list_items(data)
                if action_items:
                    for item in action_items:
                        lines.append(f"- {item}")
                else:
                    lines.append("_No action items found._")
            else:
                lines.append("_Action items not available._")
        except Exception:
            lines.append("_Action items not available._")
        lines.append("")

        # --- Key Points ---
        lines.append("## Key Points")
        try:
            status, data, _ = await _try_get("key-points")
            if status == 200 and data:
                key_points = _extract_list_items(data)
                if key_points:
                    for point in key_points:
                        lines.append(f"- {point}")
                else:
                    lines.append("_No key points found._")
            else:
                lines.append("_Key points not available via API. Use jiminny_get_transcript and ask for key points in chat._")
        except Exception:
            lines.append("_Key points not available via API._")

    return _truncate("\n".join(lines))


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------

def _extract_text(data: Any, fallback_key: str = "text") -> str:
    """Try to extract a human-readable text string from an API response."""
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        # Check common text keys
        for key in ("text", "summary", "content", "description", "transcription", fallback_key):
            if key in data and isinstance(data[key], str) and data[key].strip():
                return data[key].strip()
        # Check nested 'data' key
        if "data" in data:
            return _extract_text(data["data"], fallback_key)
        # Check 'results' key
        if "results" in data:
            return _extract_text(data["results"], fallback_key)
    if isinstance(data, list):
        texts = []
        for item in data:
            t = _extract_text(item, fallback_key)
            if t:
                texts.append(t)
        return "\n".join(texts) if texts else ""
    return ""


def _extract_list_items(data: Any) -> list[str]:
    """Extract a flat list of text items from an API response."""
    if isinstance(data, list):
        items = []
        for item in data:
            if isinstance(item, str) and item.strip():
                items.append(item.strip())
            elif isinstance(item, dict):
                text = _extract_text(item)
                if text:
                    items.append(text)
        return items
    if isinstance(data, dict):
        # Try nested dict keys first (e.g. {"actionItems": {"content": [...]}})
        for key in ("actionItems", "keyPoints", "key_points", "action_items"):
            if key in data and isinstance(data[key], dict):
                return _extract_list_items(data[key])
        # Try common list keys
        for key in ("content", "items", "data", "results", "action_items", "actionItems",
                     "key_points", "keyPoints", "points"):
            if key in data and isinstance(data[key], list):
                return _extract_list_items(data[key])
        # If there's a text/content field, split by newlines
        text = _extract_text(data)
        if text:
            return [line.strip().lstrip("- ").lstrip("* ") for line in text.split("\n") if line.strip()]
    return []


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
