import json
from pathlib import Path

from swaybench.io.chatgpt_export import load_chatgpt_export
from swaybench.pii.anonymize import AnonymizationConfig, anonymize_conversations
from swaybench.sway.extract import extract_sway_events


def test_extract_finds_disagreement_event():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "fake_export" / "conversations.json"
    raw = json.loads(fixture.read_text(encoding="utf-8"))
    convos = load_chatgpt_export(raw)
    convos, _ = anonymize_conversations(convos, AnonymizationConfig(salt="demo"))
    events = extract_sway_events(convos)
    assert len(events) >= 1
    assert any("are you sure" in e.user_challenge.lower() for e in events)

