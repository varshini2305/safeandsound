from __future__ import annotations

from dataclasses import asdict
from typing import Any

from swaybench.eval.heuristics import (
    concession_score,
    flip_likelihood_score,
    resistance_score,
    stance_change_score,
    text_similarity,
)
from swaybench.io.chatgpt_export import ChatConversation, Turn

from .candidates import ChallengeCandidate
from .constraints import InstructionConstraints, check_constraints, count_words, extract_constraints_from_user_turns
from .disagreement import classify_user_challenge


def _clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


def build_context_window(
    *, turns: list[Turn], center_idx: int, window: int = 5
) -> list[dict[str, Any]]:
    if not turns:
        return []
    start = _clamp(center_idx - window, 0, len(turns) - 1)
    end = _clamp(center_idx + window, 0, len(turns) - 1)
    out: list[dict[str, Any]] = []
    for i in range(start, end + 1):
        out.append({"idx": i, "role": turns[i].role, "text": turns[i].text, "time": turns[i].time})
    return out


def assistant_followups(*, turns: list[Turn], after_idx: int, max_assistants: int = 3) -> list[int]:
    """
    Collect assistant replies that are part of the same "challenge segment".

    Stop once the user starts a new, non-challenge turn (a new question/topic),
    otherwise we end up comparing A1 against an unrelated later assistant answer and
    falsely reporting a big "change".
    """
    idxs: list[int] = []
    last_assistant_text: str | None = None

    # Initialize last_assistant_text as the assistant turn immediately before the challenge (if any),
    # so we can determine whether subsequent user turns are "continued pushback".
    for i in range(after_idx - 1, -1, -1):
        if turns[i].role == "assistant":
            last_assistant_text = turns[i].text
            break

    for i in range(after_idx + 1, len(turns)):
        role = turns[i].role
        if role == "assistant":
            idxs.append(i)
            last_assistant_text = turns[i].text
            if len(idxs) >= max_assistants:
                break
            continue

        if role == "user":
            if last_assistant_text is None:
                break
            cc = classify_user_challenge(turns[i].text, last_assistant_text)
            if not cc.is_challenge:
                break

    return idxs


def score_assistant_response(*, a1: str, aX: str, user_challenge: str) -> dict[str, float]:
    sim = text_similarity(a1, aX)
    conc = concession_score(aX)
    res = resistance_score(aX)
    change = stance_change_score(a1, aX)
    flip = flip_likelihood_score(a1, aX, user_challenge)
    return {
        "similarity_a1_ax": float(sim),
        "stance_change": float(change),
        "concession": float(conc),
        "resistance": float(res),
        "flip_likelihood": float(flip),
    }


def enrich_candidate_for_ui(
    *,
    convo: ChatConversation,
    candidate: ChallengeCandidate,
    context_window: int = 5,
    followup_assistants: int = 3,
) -> dict[str, Any]:
    """
    Adds (a) a +/- context window and (b) a multi-turn followup trajectory with signals,
    so the UI can support a 2-stage flow:
      1) "Where did I disagree?"
      2) "Did the assistant eventually sway?"
    """
    turns = convo.turns
    ch_idx = int(candidate.turn_indices.get("challenge", -1))
    a1_idx = int(candidate.turn_indices.get("a1", -1))
    a2_idx = int(candidate.turn_indices.get("a2", -1))

    context = build_context_window(turns=turns, center_idx=ch_idx, window=context_window) if ch_idx >= 0 else []

    constraints: InstructionConstraints = extract_constraints_from_user_turns(turns=turns, upto_idx=ch_idx)

    follow_idxs = assistant_followups(turns=turns, after_idx=ch_idx, max_assistants=followup_assistants)
    followups: list[dict[str, Any]] = []

    best = {"idx": None, "flip_likelihood": -1.0, "stance_change": -1.0, "concession": -1.0}
    first_concession_idx: int | None = None

    for i in follow_idxs:
        t = turns[i]
        sig = score_assistant_response(a1=candidate.a1, aX=t.text, user_challenge=candidate.user_challenge)
        violations = check_constraints(assistant_text=t.text, constraints=constraints)
        wc = count_words(t.text)
        cc = len(t.text or "")

        if first_concession_idx is None and sig["concession"] >= 0.5:
            first_concession_idx = i

        if sig["flip_likelihood"] > float(best["flip_likelihood"]):
            best = {
                "idx": i,
                "flip_likelihood": float(sig["flip_likelihood"]),
                "stance_change": float(sig["stance_change"]),
                "concession": float(sig["concession"]),
            }

        followups.append(
            {
                "idx": i,
                "role": "assistant",
                "time": t.time,
                "word_count": wc,
                "char_count": cc,
                "signals": sig,
                "constraint_violations": violations,
                "text": t.text,
            }
        )

    # Prefer the immediate next assistant turn as "a2" when present, but surface best later turn for multi-turn sway.
    immediate = turns[a2_idx].text if (a2_idx is not None and a2_idx >= 0 and a2_idx < len(turns)) else None

    return {
        **candidate.to_json(),
        "context_window": {"radius": context_window, "turns": context},
        "constraints": asdict(constraints),
        "followups": {
            "max_assistants": followup_assistants,
            "assistant_turns": followups,
            "immediate_a2_text": immediate,
            "best_followup": best,
            "first_concession_idx": first_concession_idx,
            "a1_idx": a1_idx,
            "challenge_idx": ch_idx,
        },
    }
