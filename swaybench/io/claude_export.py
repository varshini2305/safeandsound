from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Union

from swaybench.io.chatgpt_export import ChatConversation, Turn


Sender = Literal["human", "assistant"]


def load_claude_export(data: Union[bytes, list[dict[str, Any]]]) -> list[ChatConversation]:
    """
    Load Claude export data from bytes or already-parsed JSON.

    - bytes: contents of conversations.json
    - list[dict]: parsed conversations list
    """
    if isinstance(data, (bytes, bytearray)):
        rows = json.loads(bytes(data).decode("utf-8"))
    else:
        rows = data
    if not isinstance(rows, list):
        return []
    return [_parse_conversation(c) for c in rows if isinstance(c, dict)]


def load_claude_export_from_path(path: str | Path) -> list[ChatConversation]:
    """
    Load an Anthropic Claude export.

    Expected structure (as observed in exported bundles):
      - conversations.json: list of conversations
      - each conversation has chat_messages: list of {sender: human|assistant, text: str, created_at: str}

    `path` can be:
      - a directory containing conversations.json
      - a direct path to conversations.json
    """
    p = Path(path).expanduser().resolve()
    if p.is_dir():
        p = p / "conversations.json"
    rows = json.loads(p.read_text(encoding="utf-8"))
    return load_claude_export(rows)


def _parse_conversation(c: dict[str, Any]) -> ChatConversation:
    convo_id = str(c.get("uuid") or c.get("id") or "")
    title = c.get("name") or c.get("title")
    created_at = _parse_time(c.get("created_at"))

    messages = c.get("chat_messages") or c.get("messages") or []
    turns: list[Turn] = []
    if isinstance(messages, list):
        for m in messages:
            if not isinstance(m, dict):
                continue
            sender = str(m.get("sender") or "").lower()
            role = "assistant" if sender == "assistant" else "user" if sender == "human" else "system"
            text = m.get("text")
            if not isinstance(text, str) or not text.strip():
                # Some exports also include "content"; best-effort fallback.
                content = m.get("content")
                if isinstance(content, str):
                    text = content
                else:
                    continue
            turns.append(Turn(role=role, text=text, time=_parse_time(m.get("created_at"))))

    return ChatConversation(
        conversation_id=convo_id,
        title=title if isinstance(title, str) else None,
        create_time=created_at,
        turns=turns,
    )


def _parse_time(value: object) -> float | None:
    if not isinstance(value, str) or not value:
        return None
    s = value.strip()
    try:
        # Handle "Z" suffix.
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return None
