from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .patterns import (
    AWS_KEY_RE,
    CC_CANDIDATE_RE,
    ACCOUNT_NUM_RE,
    EMAIL_RE,
    GOOGLE_KEY_RE,
    IBAN_RE,
    IP_RE,
    OPENAI_KEY_RE,
    PHONE_RE,
    ROUTING_9_RE,
    SSN_RE,
    SWIFT_BIC_RE,
    URL_RE,
)

from .hf_ner import detect_pii_hf as _detect_pii_hf


@dataclass(frozen=True)
class EntitySpan:
    start: int
    end: int
    entity_type: str
    text: str


def detect_pii(
    text: str,
    *,
    redact_urls: bool = False,
    enable_presidio: bool = False,
    enable_hf: bool = False,
    hf_model: str = "gravitee-io/bert-small-pii-detection",
) -> list[EntitySpan]:
    spans: list[EntitySpan] = []

    spans.extend(_find_spans(EMAIL_RE, text, "EMAIL"))
    spans.extend(_find_spans(PHONE_RE, text, "PHONE"))
    spans.extend(_find_spans(SSN_RE, text, "US_SSN"))
    spans.extend(_find_spans(OPENAI_KEY_RE, text, "API_KEY"))
    spans.extend(_find_spans(AWS_KEY_RE, text, "API_KEY"))
    spans.extend(_find_spans(GOOGLE_KEY_RE, text, "API_KEY"))
    spans.extend(_find_ip_spans(text))
    spans.extend(_find_credit_card_spans(text))
    spans.extend(_find_banking_spans(text))
    if redact_urls:
        spans.extend(_find_spans(URL_RE, text, "URL"))

    if enable_presidio:
        spans.extend(_presidio_spans(text))

    if enable_hf:
        spans.extend(_convert_hf_spans(_detect_pii_hf(text, model_id=hf_model)))

    return _dedupe_and_sort(spans)


def _convert_hf_spans(hf_spans: list[object]) -> list[EntitySpan]:
    out: list[EntitySpan] = []
    for s in hf_spans:
        start = getattr(s, "start", None)
        end = getattr(s, "end", None)
        entity_type = getattr(s, "entity_type", None)
        text = getattr(s, "text", None)
        if isinstance(start, int) and isinstance(end, int) and isinstance(entity_type, str) and isinstance(text, str):
            out.append(EntitySpan(start=start, end=end, entity_type=entity_type, text=text))
    return out


def _find_spans(regex, text: str, entity_type: str) -> list[EntitySpan]:
    out = []
    for m in regex.finditer(text):
        out.append(EntitySpan(start=m.start(), end=m.end(), entity_type=entity_type, text=m.group(0)))
    return out


def _find_ip_spans(text: str) -> list[EntitySpan]:
    out = []
    for m in IP_RE.finditer(text):
        s = m.group(0)
        parts = s.split(".")
        try:
            nums = [int(p) for p in parts]
        except ValueError:
            continue
        if all(0 <= n <= 255 for n in nums):
            out.append(EntitySpan(start=m.start(), end=m.end(), entity_type="IP_ADDRESS", text=s))
    return out


def _find_credit_card_spans(text: str) -> list[EntitySpan]:
    out = []
    for m in CC_CANDIDATE_RE.finditer(text):
        s = m.group(0)
        digits = "".join([c for c in s if c.isdigit()])
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            out.append(EntitySpan(start=m.start(), end=m.end(), entity_type="CREDIT_CARD", text=s))
    return out


def _find_banking_spans(text: str) -> list[EntitySpan]:
    """
    Conservative banking detection:
      - IBAN / SWIFT can be matched directly.
      - Routing/account numbers require nearby banking keywords to reduce false positives.
    """
    out: list[EntitySpan] = []
    out.extend(_find_spans(IBAN_RE, text, "IBAN"))
    out.extend(_find_spans(SWIFT_BIC_RE, text, "SWIFT_BIC"))

    lowered = text.lower()
    keywords = (
        "routing",
        "account number",
        "acct",
        "iban",
        "swift",
        "bic",
        "aba",
        "sort code",
        "bank",
    )
    if any(k in lowered for k in keywords):
        for m in ROUTING_9_RE.finditer(text):
            candidate = m.group(0)
            if _aba_routing_ok(candidate):
                out.append(EntitySpan(start=m.start(), end=m.end(), entity_type="ROUTING_NUMBER", text=candidate))
        for m in ACCOUNT_NUM_RE.finditer(text):
            candidate = m.group(0)
            # Avoid duplicating routing numbers
            if len(candidate) == 9 and _aba_routing_ok(candidate):
                continue
            out.append(EntitySpan(start=m.start(), end=m.end(), entity_type="BANK_ACCOUNT", text=candidate))

    return out


def _aba_routing_ok(digits: str) -> bool:
    if len(digits) != 9 or not digits.isdigit():
        return False
    # ABA routing checksum: (3*(d1+d4+d7) + 7*(d2+d5+d8) + (d3+d6+d9)) % 10 == 0
    d = [int(x) for x in digits]
    checksum = 3 * (d[0] + d[3] + d[6]) + 7 * (d[1] + d[4] + d[7]) + (d[2] + d[5] + d[8])
    return checksum % 10 == 0


def _luhn_ok(digits: str) -> bool:
    total = 0
    parity = len(digits) % 2
    for i, ch in enumerate(digits):
        d = ord(ch) - ord("0")
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _presidio_spans(text: str) -> list[EntitySpan]:
    try:
        from presidio_analyzer import AnalyzerEngine  # type: ignore
    except Exception:
        return []

    try:
        engine = AnalyzerEngine()
        results = engine.analyze(text=text, language="en")
    except Exception:
        return []

    out: list[EntitySpan] = []
    for r in results:
        entity = str(getattr(r, "entity_type", "PII"))
        start = int(getattr(r, "start", 0))
        end = int(getattr(r, "end", 0))
        if 0 <= start < end <= len(text):
            out.append(EntitySpan(start=start, end=end, entity_type=entity, text=text[start:end]))
    return out


def _dedupe_and_sort(spans: Iterable[EntitySpan]) -> list[EntitySpan]:
    seen = set()
    out = []
    for s in spans:
        key = (s.start, s.end, s.entity_type)
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    out.sort(key=lambda x: (x.start, -(x.end - x.start)))
    return out
