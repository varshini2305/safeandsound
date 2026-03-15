from __future__ import annotations

from typing import Any

_PIPE = None
_PIPE_MODEL = None


def _load_pipeline(model: str):
    global _PIPE, _PIPE_MODEL
    if _PIPE is not None and _PIPE_MODEL == model:
        return _PIPE
    try:
        from transformers import pipeline  # type: ignore
    except Exception:
        return None
    try:
        _PIPE = pipeline("text-classification", model=model, top_k=None)
        _PIPE_MODEL = model
        return _PIPE
    except Exception:
        return None


def _normalize_label(label: str) -> str:
    l = (label or "").lower()
    if "contrad" in l:
        return "contradiction"
    if "entail" in l:
        return "entailment"
    if "neutral" in l:
        return "neutral"
    return l or "unknown"


def nli_scores(
    *, pairs: list[tuple[str, str]], model: str
) -> list[dict[str, Any]] | None:
    """
    Returns NLI scores for (premise, hypothesis) pairs, if transformers is installed.
    Output dict has probabilities for entailment/neutral/contradiction when possible.
    """
    pipe = _load_pipeline(model)
    if pipe is None:
        return None

    inputs = [{"text": p, "text_pair": h} for p, h in pairs]
    try:
        outputs = pipe(inputs)
    except Exception:
        return None

    out: list[dict[str, Any]] = []
    for o in outputs:
        # Expected: list of {label, score} or single dict
        items = o if isinstance(o, list) else [o]
        scores = {"entailment": 0.0, "neutral": 0.0, "contradiction": 0.0}
        best = ("unknown", 0.0)
        for it in items:
            if not isinstance(it, dict):
                continue
            lab = _normalize_label(str(it.get("label") or ""))
            sc = float(it.get("score") or 0.0)
            if lab in scores:
                scores[lab] = max(scores[lab], sc)
            if sc > best[1]:
                best = (lab, sc)
        out.append({"label": best[0], "confidence": best[1], **scores})
    return out

