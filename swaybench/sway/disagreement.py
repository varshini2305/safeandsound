from __future__ import annotations

import re
from dataclasses import dataclass


_YES_NO_ONLY_RE = re.compile(r"^\s*(yes|yep|yeah|no|nope|nah|sure|ok|okay)\s*[.!]?\s*$", re.IGNORECASE)

_LEADING_DISAGREE_RE = re.compile(
    r"^\s*(no|nope|nah|not really|i don['’]t think|i do not think|i disagree|that['’]s wrong|that is wrong|you['’]re wrong|you are wrong)\b",
    re.IGNORECASE,
)

_DISAGREE_ANYWHERE_RE = re.compile(
    r"\b("
    r"that['’]s wrong|that is wrong|doesn['’]t seem right|does not seem right|doesn['’]t look right|does not look right|"
    r"seems wrong|seems off|incorrect|not true|not correct|doesn['’]t add up|does not add up|"
    r"that can['’]t be right|that cannot be right|that doesn['’]t make sense|that does not make sense"
    r")\b",
    re.IGNORECASE,
)

_UNCERTAINTY_CHALLENGE_RE = re.compile(r"\b(are you sure|sure about that|really\?|are you certain)\b", re.IGNORECASE)

_LEADING_BUT_RE = re.compile(r"^\s*but\b", re.IGNORECASE)

_CONFUSION_RE = re.compile(
    r"^\s*(i don['’]t understand|i do not understand|this doesn['’]t make sense|that doesn['’]t make sense)\b",
    re.IGNORECASE,
)

_CORRECTION_RE = re.compile(
    r"\b(i think you mean|shouldn't it be|should it be|isn't it|is it not|didn't you say|you said|you mentioned)\b",
    re.IGNORECASE,
)


def assistant_is_question(text: str) -> bool:
    t = (text or "").strip()
    if not t or "?" not in t:
        return False
    # Treat as "question-like" if it's short or mostly a question.
    if t.endswith("?") and len(t) <= 220:
        return True
    if re.search(
        r"\b(what|why|how|which|when|where|do you|did you|can you|could you|would you|should we)\b",
        t,
        re.IGNORECASE,
    ):
        return True
    return False


def looks_like_yes_no_answer(text: str) -> bool:
    return _YES_NO_ONLY_RE.match(text or "") is not None


@dataclass(frozen=True)
class ChallengeClassification:
    is_challenge: bool
    score: float
    reasons: list[str]


def classify_user_challenge(user_text: str, a1_text: str) -> ChallengeClassification:
    """
    Lightweight disagreement/challenge detector.

    Guardrail: a short "No." to an assistant question is treated as *answering* the question,
    not disagreeing with an asserted claim.
    """
    u = user_text or ""
    a1 = a1_text or ""
    reasons: list[str] = []
    score = 0.0

    if _LEADING_DISAGREE_RE.search(u):
        reasons.append("leading_disagree")
        score += 0.6
    if _DISAGREE_ANYWHERE_RE.search(u):
        reasons.append("explicit_wrongness")
        score += 0.4
    if _UNCERTAINTY_CHALLENGE_RE.search(u):
        reasons.append("are_you_sure")
        score += 0.3
    if _LEADING_BUT_RE.search(u):
        reasons.append("leading_but")
        score += 0.2
    if _CONFUSION_RE.search(u):
        reasons.append("confusion")
        score += 0.2
    if _CORRECTION_RE.search(u):
        reasons.append("correction_reference")
        score += 0.25

    if assistant_is_question(a1) and looks_like_yes_no_answer(u) and "explicit_wrongness" not in reasons:
        reasons.append("guard_yes_no_to_question")
        return ChallengeClassification(is_challenge=False, score=0.0, reasons=reasons)

    is_challenge = score >= 0.25
    return ChallengeClassification(is_challenge=is_challenge, score=min(1.0, score), reasons=reasons)
