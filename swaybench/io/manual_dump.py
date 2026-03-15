from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from swaybench.io.chatgpt_export import ChatConversation, Turn


def load_manual_thread_dump(rows: list[dict[str, Any]]) -> list[ChatConversation]:
    """
    Load a manually constructed "thread dump" shaped like:
      [
        {"thread_title": str, "timezone": str?, "messages": [{"role": "...", "content": "..."}]}
      ]
    """
    out: list[ChatConversation] = []
    for idx, t in enumerate(rows):
        if not isinstance(t, dict):
            continue
        msgs = t.get("messages")
        if not isinstance(msgs, list):
            continue
        title = t.get("thread_title")
        turns: list[Turn] = []
        for m in msgs:
            if not isinstance(m, dict):
                continue
            role = str(m.get("role") or "system").lower()
            if role not in ("user", "assistant", "system"):
                role = "system"
            content = m.get("content")
            if not isinstance(content, str) or not content.strip():
                continue
            turns.append(Turn(role=role, text=content, time=None))
        if not turns:
            continue
        out.append(
            ChatConversation(
                conversation_id=str(t.get("thread_id") or t.get("id") or f"manual_{idx:04d}"),
                title=title if isinstance(title, str) else None,
                create_time=None,
                turns=turns,
            )
        )
    return out

