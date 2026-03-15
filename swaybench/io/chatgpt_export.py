from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass
from typing import Any, Iterable, Literal, Union


Role = Literal["user", "assistant", "system"]


@dataclass(frozen=True)
class Turn:
    role: Role
    text: str
    time: float | None = None


@dataclass(frozen=True)
class ChatConversation:
    conversation_id: str
    title: str | None
    create_time: float | None
    turns: list[Turn]


def load_chatgpt_export(data: Union[bytes, list[dict[str, Any]]]) -> list[ChatConversation]:
    """
    Load ChatGPT export data.

    Accepts:
      - bytes: a .zip containing conversations.json
      - list[dict]: the parsed JSON value of conversations.json
    """
    if isinstance(data, (bytes, bytearray)):
        conversations = _read_zip_conversations_json(bytes(data))
    else:
        conversations = data
    return [_parse_conversation(c) for c in conversations if isinstance(c, dict)]


def _read_zip_conversations_json(zip_bytes: bytes) -> list[dict[str, Any]]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        with zf.open("conversations.json") as f:
            return json.loads(f.read().decode("utf-8"))


def _parse_conversation(c: dict[str, Any]) -> ChatConversation:
    conversation_id = str(c.get("id") or c.get("conversation_id") or "")
    title = c.get("title")
    create_time = c.get("create_time")

    mapping: dict[str, Any] = c.get("mapping") or {}
    current_node = c.get("current_node")

    turns: list[Turn] = []
    node_ids = _primary_node_path(mapping, current_node)
    for node_id in node_ids:
        node = mapping.get(node_id) or {}
        message = node.get("message")
        if not isinstance(message, dict):
            continue
        role = _normalize_role(((message.get("author") or {}).get("role")) or "system")
        text = _message_text(message)
        if not text.strip():
            continue
        turns.append(Turn(role=role, text=text, time=message.get("create_time")))

    if not turns:
        turns = _fallback_extract_turns(mapping.values())

    return ChatConversation(
        conversation_id=conversation_id,
        title=title,
        create_time=create_time,
        turns=turns,
    )


def _primary_node_path(mapping: dict[str, Any], current_node: str | None) -> list[str]:
    if not mapping:
        return []

    leaf = current_node if isinstance(current_node, str) and current_node in mapping else None
    if leaf is None:
        leaf = _find_any_leaf(mapping)
    if leaf is None:
        return []

    path = []
    seen = set()
    node_id = leaf
    while node_id and node_id not in seen:
        seen.add(node_id)
        path.append(node_id)
        node = mapping.get(node_id) or {}
        parent = node.get("parent")
        node_id = parent if isinstance(parent, str) else None
    path.reverse()
    return path


def _find_any_leaf(mapping: dict[str, Any]) -> str | None:
    for node_id, node in mapping.items():
        children = node.get("children")
        if isinstance(children, list) and len(children) == 0:
            return node_id
    return next(iter(mapping.keys()), None)


def _fallback_extract_turns(nodes: Iterable[Any]) -> list[Turn]:
    msgs = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        message = node.get("message")
        if not isinstance(message, dict):
            continue
        text = _message_text(message).strip()
        if not text:
            continue
        role = _normalize_role(((message.get("author") or {}).get("role")) or "system")
        msgs.append((message.get("create_time") or 0.0, Turn(role=role, text=text, time=message.get("create_time"))))
    msgs.sort(key=lambda x: x[0])
    return [m for _, m in msgs]


def _normalize_role(role: str) -> Role:
    r = role.lower()
    if r in ("assistant", "user"):
        return r  # type: ignore[return-value]
    return "system"


def _message_text(message: dict[str, Any]) -> str:
    content = message.get("content") or {}
    parts = content.get("parts")
    if isinstance(parts, list):
        return "\n".join([p for p in parts if isinstance(p, str)])
    text = content.get("text")
    return text if isinstance(text, str) else ""

