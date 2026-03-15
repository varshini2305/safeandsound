import json
from pathlib import Path

from swaybench.io.manual_dump import load_manual_thread_dump
from swaybench.pii.anonymize import AnonymizationConfig, anonymize_conversations_with_state
from swaybench.sway.candidates import extract_challenge_candidates
from swaybench.sway.enrich import enrich_candidate_for_ui


def test_enriched_candidate_includes_context_and_followups() -> None:
    path = Path("data_exports/openai/chatgpt_convo_dump_augmented.json")
    rows = json.loads(path.read_text(encoding="utf-8"))
    convos = load_manual_thread_dump(rows)

    # Sanitize first so the flow matches the app pipeline.
    convos_s, _, _state = anonymize_conversations_with_state(convos, AnonymizationConfig(salt="demo"))
    candidates = extract_challenge_candidates(convos_s, min_score=0.25)
    assert candidates, "Expected at least one candidate in augmented dump"

    convo_by_id = {c.conversation_id: c for c in convos_s}
    c0 = candidates[0]
    enriched = enrich_candidate_for_ui(convo=convo_by_id[c0.convo_id], candidate=c0, context_window=5, followup_assistants=4)

    assert "context_window" in enriched
    assert len(enriched["context_window"]["turns"]) >= 3
    assert "followups" in enriched
    assert "assistant_turns" in enriched["followups"]

