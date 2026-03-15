from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Dict, Literal, Tuple

from pydantic import BaseModel

from swaybench.io.chatgpt_export import ChatConversation, Turn

from .detect import EntitySpan, detect_pii


class PiiSummary(BaseModel):
    total_spans: int
    entity_counts: dict[str, int]
    top_conversations: list[dict[str, object]]

class PiiSpanPreview(BaseModel):
    start: int
    end: int
    entity_type: str
    original: str
    replacement: str
    line_no: int
    original_line: str
    sanitized_line: str
    line_span_start: int
    line_span_end: int


class PiiTurnPreview(BaseModel):
    role: str
    original_line: str
    sanitized_line: str
    spans: list[PiiSpanPreview]


class PiiConversationPreview(BaseModel):
    conversation_id: str
    title: str | None
    turns: list[PiiTurnPreview]


class PiiPreview(BaseModel):
    conversations: list[PiiConversationPreview]


@dataclass
class AnonymizationState:
    mapping: dict[Tuple[str, str], str]
    type_counters: dict[str, int]


AnonymizationMode = Literal["placeholder", "synthetic"]


@dataclass(frozen=True)
class AnonymizationConfig:
    salt: str
    redact_urls: bool = False
    enable_presidio: bool = False
    enable_hf: bool = False
    hf_model: str = "gravitee-io/bert-small-pii-detection"
    mode: AnonymizationMode = "placeholder"


def anonymize_conversations(
    conversations: list[ChatConversation], cfg: AnonymizationConfig
) -> tuple[list[ChatConversation], PiiSummary]:
    sanitized, summary, _state = anonymize_conversations_with_state(conversations, cfg)
    return sanitized, summary


def anonymize_conversations_with_state(
    conversations: list[ChatConversation],
    cfg: AnonymizationConfig,
    state: AnonymizationState | None = None,
) -> tuple[list[ChatConversation], PiiSummary, AnonymizationState]:
    entity_counts: dict[str, int] = {}
    convo_spans: list[tuple[str, str | None, int]] = []

    if state is None:
        state = AnonymizationState(mapping={}, type_counters={})

    out_conversations: list[ChatConversation] = []

    for convo in conversations:
        convo_span_count = 0
        new_turns: list[Turn] = []
        for t in convo.turns:
            spans = detect_pii(
                t.text,
                redact_urls=cfg.redact_urls,
                enable_presidio=cfg.enable_presidio,
                enable_hf=cfg.enable_hf,
                hf_model=cfg.hf_model,
            )
            convo_span_count += len(spans)
            for s in spans:
                entity_counts[s.entity_type] = entity_counts.get(s.entity_type, 0) + 1
            sanitized = _replace_spans(t.text, spans, cfg, state.mapping, state.type_counters)
            new_turns.append(Turn(role=t.role, text=sanitized, time=t.time))

        convo_spans.append((convo.conversation_id, convo.title, convo_span_count))
        out_conversations.append(
            ChatConversation(
                conversation_id=convo.conversation_id,
                title=convo.title,
                create_time=convo.create_time,
                turns=new_turns,
            )
        )

    top = sorted(convo_spans, key=lambda x: x[2], reverse=True)[:20]
    top_rows = [
        {"conversation_id": cid, "title": title, "detected_spans": n} for cid, title, n in top if n > 0
    ]

    return (
        out_conversations,
        PiiSummary(
            total_spans=sum(entity_counts.values()),
            entity_counts=dict(sorted(entity_counts.items())),
            top_conversations=top_rows,
        ),
        state,
    )


def build_pii_preview(
    original: list[ChatConversation],
    sanitized: list[ChatConversation],
    cfg: AnonymizationConfig,
    state: AnonymizationState,
    *,
    conversation_ids: list[str],
    max_turns_per_conversation: int = 10,
) -> PiiPreview:
    by_id_orig = {c.conversation_id: c for c in original}
    by_id_san = {c.conversation_id: c for c in sanitized}
    previews: list[PiiConversationPreview] = []

    for cid in conversation_ids:
        o = by_id_orig.get(cid)
        s = by_id_san.get(cid)
        if o is None or s is None:
            continue
        turns: list[PiiTurnPreview] = []
        for ot, st in zip(o.turns, s.turns):
            spans = detect_pii(
                ot.text,
                redact_urls=cfg.redact_urls,
                enable_presidio=cfg.enable_presidio,
                enable_hf=cfg.enable_hf,
                hf_model=cfg.hf_model,
            )
            if not spans:
                continue
            spans = _non_overlapping(spans)
            out_spans: list[PiiSpanPreview] = []
            san_lines = st.text.split("\n")
            for sp in spans[:50]:
                orig_slice = ot.text[sp.start : sp.end]
                key = (sp.entity_type, _stable_key(orig_slice, cfg.salt))
                replacement = state.mapping.get(key)
                if not replacement:
                    continue
                line_no, line_start, line_end = _line_bounds(ot.text, sp.start)
                original_line = ot.text[line_start:line_end]
                sanitized_line = san_lines[line_no] if 0 <= line_no < len(san_lines) else st.text
                out_spans.append(
                    PiiSpanPreview(
                        start=sp.start,
                        end=sp.end,
                        entity_type=sp.entity_type,
                        original=orig_slice,
                        replacement=replacement,
                        line_no=line_no,
                        original_line=original_line,
                        sanitized_line=sanitized_line,
                        line_span_start=sp.start - line_start,
                        line_span_end=sp.end - line_start,
                    )
                )
            if not out_spans:
                continue
            turns.append(
                PiiTurnPreview(
                    role=ot.role,
                    original_line=out_spans[0].original_line,
                    sanitized_line=out_spans[0].sanitized_line,
                    spans=out_spans,
                )
            )
            if len(turns) >= max_turns_per_conversation:
                break
        if turns:
            previews.append(
                PiiConversationPreview(conversation_id=cid, title=o.title, turns=turns)
            )
    return PiiPreview(conversations=previews)


def _line_bounds(text: str, idx: int) -> tuple[int, int, int]:
    """
    Return (line_no, line_start, line_end) for the line containing text[idx].
    """
    if idx < 0:
        idx = 0
    if idx > len(text):
        idx = len(text)
    line_no = text[:idx].count("\n")
    line_start = text.rfind("\n", 0, idx)
    line_start = 0 if line_start == -1 else line_start + 1
    line_end = text.find("\n", idx)
    line_end = len(text) if line_end == -1 else line_end
    return line_no, line_start, line_end


def _replace_spans(
    text: str,
    spans: list[EntitySpan],
    cfg: AnonymizationConfig,
    mapping: Dict[Tuple[str, str], str],
    type_counters: Dict[str, int],
) -> str:
    spans = _non_overlapping(spans)
    if not spans:
        return text

    out = text
    for s in sorted(spans, key=lambda x: x.start, reverse=True):
        original = out[s.start : s.end]
        key = (s.entity_type, _stable_key(original, cfg.salt))
        replacement = mapping.get(key)
        if replacement is None:
            type_counters[s.entity_type] = type_counters.get(s.entity_type, 0) + 1
            idx = type_counters[s.entity_type]
            replacement = (
                f"<{s.entity_type}_{idx}>"
                if cfg.mode == "placeholder"
                else _synthetic_value(s.entity_type, idx, cfg.salt)
            )
            mapping[key] = replacement
        out = out[: s.start] + replacement + out[s.end :]
    return out


def _stable_key(value: str, salt: str) -> str:
    h = hashlib.sha256()
    h.update(salt.encode("utf-8"))
    h.update(b"\x00")
    h.update(value.strip().lower().encode("utf-8"))
    return h.hexdigest()


def _synthetic_value(entity_type: str, idx: int, salt: str) -> str:
    """
    Deterministic, fake-but-plausible replacements.
    Uses reserved/example formats where possible (e.g., example.com, 555-01xx, 192.0.2.x).
    """
    seed = int(hashlib.sha256(f"{salt}|{entity_type}|{idx}".encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed)

    et = entity_type.upper()
    if et in ("EMAIL", "EMAIL_ADDRESS"):
        adj = rng.choice(["quick", "calm", "bright", "silent", "curious", "brave", "gentle", "clever"])
        noun = rng.choice(["otter", "panda", "falcon", "maple", "stone", "river", "cobalt", "comet"])
        return f"{adj}.{noun}.{idx}@example.com"
    if et in ("PHONE", "PHONE_NUMBER"):
        area = rng.choice(["212", "415", "617", "206", "650"])
        return f"+1 ({area}) 555-01{idx % 100:02d}"
    if et in ("US_SSN", "SSN"):
        return f"000-00-{idx % 10000:04d}"
    if et in ("CREDIT_CARD", "CREDITCARD"):
        return f"0000 0000 0000 {idx % 10000:04d}"
    if et in ("IP_ADDRESS", "IP"):
        return f"192.0.2.{(idx % 250) + 1}"
    if et in ("URL", "URI"):
        return f"https://example.com/resource/{idx}"
    if et in ("API_KEY", "TOKEN", "SECRET"):
        suffix = hashlib.sha256(f"{salt}|{idx}".encode("utf-8")).hexdigest()[:24]
        return f"sk-fake-{suffix}"
    if et in ("PERSON", "PERSON_NAME"):
        first = rng.choice(["Alex", "Sam", "Jordan", "Taylor", "Casey", "Riley", "Morgan", "Avery"])
        last = rng.choice(["Kim", "Patel", "Nguyen", "Garcia", "Smith", "Chen", "Johnson", "Khan"])
        return f"{first} {last}"
    if et in ("LOCATION", "GPE", "CITY"):
        return rng.choice(["Springfield, CA", "Riverton, WA", "Lakeside, TX", "Fairview, NY"])
    if et in ("ADDRESS", "STREET_ADDRESS"):
        return f"{100 + (idx % 800)} Example St, Springfield, CA 9410{idx % 10}"

    return f"<{entity_type}_{idx}>"


def _non_overlapping(spans: list[EntitySpan]) -> list[EntitySpan]:
    if not spans:
        return []
    spans = sorted(spans, key=lambda x: (x.start, -(x.end - x.start)))
    out: list[EntitySpan] = []
    last_end = -1
    for s in spans:
        if s.start < last_end:
            continue
        out.append(s)
        last_end = s.end
    return out
