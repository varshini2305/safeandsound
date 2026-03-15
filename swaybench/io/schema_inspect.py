from __future__ import annotations

from collections import Counter
from typing import Any


def schema_summary(obj: Any, *, max_conversations: int = 200, max_messages: int = 2000) -> dict[str, Any]:
    """
    Deterministic structural summary for debugging/UX.
    Does not return raw message content.
    """
    if not isinstance(obj, list):
        return {"kind": type(obj).__name__}

    convo_key_sets: Counter[str] = Counter()
    msg_key_sets: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    content_type_counts: Counter[str] = Counter()

    convos = [c for c in obj[:max_conversations] if isinstance(c, dict)]
    for c in convos:
        convo_key_sets[_key_sig(c)] += 1

        # Claude
        if isinstance(c.get("chat_messages"), list):
            for m in c["chat_messages"][: max_messages]:
                if not isinstance(m, dict):
                    continue
                msg_key_sets[_key_sig(m)] += 1
                role_counts[str(m.get("sender") or "unknown").lower()] += 1
        # Manual dump
        elif isinstance(c.get("messages"), list):
            for m in c["messages"][: max_messages]:
                if not isinstance(m, dict):
                    continue
                msg_key_sets[_key_sig(m)] += 1
                role_counts[str(m.get("role") or "unknown").lower()] += 1
        # ChatGPT export graph
        elif isinstance(c.get("mapping"), dict):
            mapping = c["mapping"]
            for node in list(mapping.values())[: max_messages]:
                if not isinstance(node, dict):
                    continue
                msg = node.get("message")
                if not isinstance(msg, dict):
                    continue
                msg_key_sets[_key_sig(msg)] += 1
                author = msg.get("author") or {}
                if isinstance(author, dict):
                    role_counts[str(author.get("role") or "unknown").lower()] += 1
                content = msg.get("content") or {}
                if isinstance(content, dict):
                    ct = content.get("content_type")
                    if isinstance(ct, str):
                        content_type_counts[ct] += 1

    return {
        "kind": "list",
        "conversations_sampled": len(convos),
        "conversation_key_patterns": _top(convo_key_sets),
        "message_key_patterns": _top(msg_key_sets),
        "role_counts": dict(role_counts),
        "content_type_counts": dict(content_type_counts),
    }


def _key_sig(d: dict[str, Any]) -> str:
    return ",".join(sorted(d.keys()))


def _top(c: Counter[str], n: int = 5) -> list[dict[str, Any]]:
    total = sum(c.values()) or 1
    out = []
    for k, v in c.most_common(n):
        out.append({"keys": k.split(",") if k else [], "count": v, "pct": round(v / total, 4)})
    return out

