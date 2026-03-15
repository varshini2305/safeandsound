from __future__ import annotations

import re
from dataclasses import dataclass


_WORD_LIMIT_RE = re.compile(
    r"(?:<=\s*(\d+)\s*words?)|(?:under\s*(\d+)\s*words?)|(?:max(?:imum)?\s*(\d+)\s*words?)",
    re.IGNORECASE,
)
_CHAR_LIMIT_RE = re.compile(
    r"(?:<=\s*(\d+)\s*(?:characters|chars))|(?:under\s*(\d+)\s*(?:characters|chars))|(?:max(?:imum)?\s*(\d+)\s*(?:characters|chars))",
    re.IGNORECASE,
)
_RELEVANT_ONLY_RE = re.compile(
    r"\b(only include|keep it)\b.*\b(relevant|role-?relevant|directly relevant)\b", re.IGNORECASE
)
_CONCISE_SOFT_RE = re.compile(r"\b(keep it|make it)\b.*\b(concise|shorter|short|brief)\b", re.IGNORECASE)


@dataclass(frozen=True)
class InstructionConstraints:
    word_limit: int | None = None
    char_limit: int | None = None
    relevant_only: bool = False
    soft_concise: bool = False
    sources: list[dict[str, object]] | None = None


def extract_constraints_from_user_turns(
    *, turns: list[object], upto_idx: int
) -> InstructionConstraints:
    """
    Heuristic constraint miner for subtle qualitative 'instruction drift' cases.
    Scans user turns up to `upto_idx` (inclusive) for constraints like:
      - <= N words / under N words
      - <= N characters
      - "only include relevant details"
      - "keep it concise" (soft)
    """
    word_limit: int | None = None
    char_limit: int | None = None
    relevant_only = False
    soft_concise = False
    sources: list[dict[str, object]] = []

    for i in range(0, min(len(turns), upto_idx + 1)):
        t = turns[i]
        role = getattr(t, "role", None)
        if role != "user":
            continue
        text = str(getattr(t, "text", "") or "")

        m = _WORD_LIMIT_RE.search(text)
        if m:
            n = next((g for g in m.groups() if g), None)
            if n:
                try:
                    word_limit = int(n)
                    sources.append({"idx": i, "kind": "word_limit", "value": word_limit})
                except Exception:
                    pass

        m = _CHAR_LIMIT_RE.search(text)
        if m:
            n = next((g for g in m.groups() if g), None)
            if n:
                try:
                    char_limit = int(n)
                    sources.append({"idx": i, "kind": "char_limit", "value": char_limit})
                except Exception:
                    pass

        if _RELEVANT_ONLY_RE.search(text):
            relevant_only = True
            sources.append({"idx": i, "kind": "relevant_only"})

        if _CONCISE_SOFT_RE.search(text):
            soft_concise = True
            sources.append({"idx": i, "kind": "soft_concise"})

    return InstructionConstraints(
        word_limit=word_limit,
        char_limit=char_limit,
        relevant_only=relevant_only,
        soft_concise=soft_concise,
        sources=sources[:40],
    )


def count_words(text: str) -> int:
    return len([w for w in (text or "").strip().split() if w])


def check_constraints(*, assistant_text: str, constraints: InstructionConstraints) -> list[dict[str, object]]:
    """
    Returns a list of machine-readable violations.
    """
    text = assistant_text or ""
    wc = count_words(text)
    cc = len(text)
    out: list[dict[str, object]] = []

    if constraints.word_limit is not None and wc > constraints.word_limit:
        out.append(
            {
                "type": "word_limit",
                "limit": constraints.word_limit,
                "observed": wc,
                "over_by": wc - constraints.word_limit,
            }
        )

    if constraints.char_limit is not None and cc > constraints.char_limit:
        out.append(
            {
                "type": "char_limit",
                "limit": constraints.char_limit,
                "observed": cc,
                "over_by": cc - constraints.char_limit,
            }
        )

    return out

