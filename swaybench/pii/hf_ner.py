from __future__ import annotations

from typing import Any


def detect_pii_hf(
    text: str,
    *,
    model_id: str,
    max_chars: int = 6000,
    chunk_size: int = 1200,
    chunk_overlap: int = 100,
) -> list[EntitySpan]:
    """
    Optional HuggingFace token-classification pass to catch PII beyond regex.
    Designed to be safe when transformers/torch aren't installed: returns [].

    Notes:
      - For long texts, runs in overlapping character windows and re-maps offsets.
      - Requires the model to be available locally (first run may download weights).
    """
    if not text or not text.strip():
        return []

    # Safety/perf: don't run HF over extremely long turns by default.
    t = text
    if len(t) > max_chars:
        t = t[:max_chars]

    try:
        from transformers import pipeline  # type: ignore
    except Exception:
        return []

    try:
        nlp = pipeline(
            "token-classification",
            model=model_id,
            aggregation_strategy="simple",
        )
    except Exception:
        return []

    spans: list[EntitySpan] = []
    for base, chunk in _chunks(t, chunk_size=chunk_size, overlap=chunk_overlap):
        try:
            preds = nlp(chunk)
        except Exception:
            continue
        if not isinstance(preds, list):
            continue
        for p in preds:
            if not isinstance(p, dict):
                continue
            start = p.get("start")
            end = p.get("end")
            label = p.get("entity_group") or p.get("entity")
            if not isinstance(start, int) or not isinstance(end, int) or end <= start:
                continue
            if not isinstance(label, str):
                continue
            s = base + start
            e = base + end
            if 0 <= s < e <= len(t):
                entity_type = _map_label(label)
                spans.append(EntitySpan(start=s, end=e, entity_type=entity_type, text=t[s:e]))

    return _dedupe_and_sort(spans)


def _chunks(text: str, *, chunk_size: int, overlap: int):
    if chunk_size <= 0:
        yield 0, text
        return
    i = 0
    n = len(text)
    while i < n:
        j = min(n, i + chunk_size)
        yield i, text[i:j]
        if j == n:
            break
        i = max(0, j - overlap)


def _map_label(label: str) -> str:
    """
    Normalize common NER labels into our anonymizer's entity types.
    Falls back to the original label.
    """
    l = label.upper().replace("-", "_")
    if l in ("EMAIL", "EMAIL_ADDRESS"):
        return "EMAIL"
    if l in ("PHONE", "PHONE_NUMBER", "PHONENUMBER"):
        return "PHONE"
    if l in ("IP", "IP_ADDRESS"):
        return "IP_ADDRESS"
    if l in ("CREDIT_CARD", "CREDITCARD", "CARD_NUMBER"):
        return "CREDIT_CARD"
    if l in ("SSN", "US_SSN", "SOCIAL_SECURITY_NUMBER"):
        return "US_SSN"
    if l in ("PERSON", "PER"):
        return "PERSON"
    if l in ("LOCATION", "LOC", "GPE", "CITY", "COUNTRY", "STATE"):
        return "LOCATION"
    if l in ("ADDRESS", "STREET_ADDRESS"):
        return "ADDRESS"
    if l in ("URL", "URI"):
        return "URL"
    if l in ("ORGANIZATION", "ORG"):
        return "ORG"
    return l


def _dedupe_and_sort(spans: list[EntitySpan]) -> list[EntitySpan]:
    seen = set()
    out: list[EntitySpan] = []
    for s in spans:
        key = (s.start, s.end, s.entity_type)
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    out.sort(key=lambda x: (x.start, -(x.end - x.start)))
    return out


class EntitySpan:  # local type to avoid circular imports with detect.py
    def __init__(self, *, start: int, end: int, entity_type: str, text: str) -> None:
        self.start = start
        self.end = end
        self.entity_type = entity_type
        self.text = text

