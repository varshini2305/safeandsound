import json
from pathlib import Path

from swaybench.io.chatgpt_export import load_chatgpt_export
from swaybench.pii.anonymize import (
    AnonymizationConfig,
    anonymize_conversations_with_state,
    build_pii_preview,
)


def test_build_pii_preview_contains_replacement():
    raw = json.loads(Path("fixtures/fake_export/conversations.json").read_text(encoding="utf-8"))
    convos = load_chatgpt_export(raw)
    cfg = AnonymizationConfig(salt="demo", mode="synthetic")
    sanitized, summary, state = anonymize_conversations_with_state(convos, cfg)

    top_ids = [r["conversation_id"] for r in summary.top_conversations[:1]]
    preview = build_pii_preview(convos, sanitized, cfg, state, conversation_ids=top_ids, max_turns_per_conversation=5)
    assert len(preview.conversations) >= 1
    turn = preview.conversations[0].turns[0]
    assert len(turn.spans) >= 1
    # replacement should appear in sanitized text
    assert any(sp.replacement in sp.sanitized_line for sp in turn.spans)
