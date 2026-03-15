from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ZipJsonSelection:
    filename: str
    bytes: bytes
    reason: str


def select_json_from_zip(zip_bytes: bytes) -> ZipJsonSelection:
    """
    Given a zip (ChatGPT/Claude/manual), select the most likely conversations JSON file.

    Heuristics:
      1) exact 'conversations.json' at root
      2) any '*conversations.json' anywhere
      3) largest .json file
    """
    with zipfile.ZipFile(__import__("io").BytesIO(zip_bytes)) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]

        if "conversations.json" in names:
            return ZipJsonSelection(
                filename="conversations.json",
                bytes=zf.read("conversations.json"),
                reason="found_root_conversations.json",
            )

        conv_candidates = [n for n in names if n.lower().endswith("conversations.json")]
        if conv_candidates:
            chosen = _choose_largest(zf, conv_candidates)
            return ZipJsonSelection(
                filename=chosen,
                bytes=zf.read(chosen),
                reason="found_conversations_json_in_zip",
            )

        json_candidates = [n for n in names if n.lower().endswith(".json")]
        if not json_candidates:
            raise ValueError("No .json files found in zip")

        chosen = _choose_largest(zf, json_candidates)
        return ZipJsonSelection(
            filename=chosen,
            bytes=zf.read(chosen),
            reason="fell_back_to_largest_json",
        )


def _choose_largest(zf: zipfile.ZipFile, names: list[str]) -> str:
    best = None
    best_size = -1
    for n in names:
        try:
            info = zf.getinfo(n)
        except KeyError:
            continue
        if info.file_size > best_size:
            best = n
            best_size = info.file_size
    if best is None:
        return names[0]
    return best


def sniff_json_kind(json_bytes: bytes) -> dict[str, Any]:
    """
    Best-effort structural sniffing for upload debugging/UX.
    Returns a small report (no raw content).
    """
    try:
        obj = json.loads(json_bytes.decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": str(e)}

    report: dict[str, Any] = {"ok": True}
    report["type"] = type(obj).__name__
    if isinstance(obj, list):
        report["length"] = len(obj)
        if obj and isinstance(obj[0], dict):
            keys = sorted(list(obj[0].keys()))
            report["first_keys"] = keys[:50]
            report["looks_like_chatgpt"] = "mapping" in obj[0] or "current_node" in obj[0]
            report["looks_like_claude"] = "chat_messages" in obj[0]
            report["looks_like_manual_dump"] = "messages" in obj[0] and "thread_title" in obj[0]
    elif isinstance(obj, dict):
        report["keys"] = sorted(list(obj.keys()))[:80]
    return report
