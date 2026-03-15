from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from swaybench.io.chatgpt_export import ChatConversation, load_chatgpt_export
from swaybench.io.claude_export import load_claude_export
from swaybench.io.manual_dump import load_manual_thread_dump
from swaybench.io.zip_detect import select_json_from_zip, sniff_json_kind


DetectedFormat = Literal["chatgpt", "claude", "unknown"]
UploadKind = Literal["zip", "json"]


@dataclass(frozen=True)
class AutoLoadResult:
    conversations: list[ChatConversation]
    detected_format: DetectedFormat
    upload_kind: UploadKind
    debug: dict[str, Any]


def load_any_export(upload_bytes: bytes) -> AutoLoadResult:
    """
    Auto-detect ChatGPT zip, ChatGPT conversations.json, Claude conversations.json.
    """
    if _looks_like_zip(upload_bytes):
        sel = select_json_from_zip(upload_bytes)
        sniff = sniff_json_kind(sel.bytes)
        conversations, detected = _load_json_bytes(sel.bytes)
        return AutoLoadResult(
            conversations=conversations,
            detected_format=detected,
            upload_kind="zip",
            debug={"zip_selected": {"filename": sel.filename, "reason": sel.reason}, "sniff": sniff},
        )

    sniff = sniff_json_kind(upload_bytes)
    conversations, detected = _load_json_bytes(upload_bytes)
    return AutoLoadResult(
        conversations=conversations,
        detected_format=detected,
        upload_kind="json",
        debug={"sniff": sniff},
    )


def _load_json_bytes(b: bytes) -> tuple[list[ChatConversation], DetectedFormat]:
    try:
        obj = json.loads(b.decode("utf-8"))
    except Exception:
        return [], "unknown"

    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        if "chat_messages" in obj[0]:
            return load_claude_export(obj), "claude"
        if "mapping" in obj[0] or "current_node" in obj[0]:
            return load_chatgpt_export(obj), "chatgpt"
        if "messages" in obj[0] and "thread_title" in obj[0]:
            return load_manual_thread_dump(obj), "chatgpt"

    return [], "unknown"


def _looks_like_zip(b: bytes) -> bool:
    return len(b) >= 4 and b[0:4] == b"PK\x03\x04"
