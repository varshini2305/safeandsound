import json
from pathlib import Path

from swaybench.io.manual_dump import load_manual_thread_dump
from swaybench.sway.candidates import extract_challenge_candidates
from swaybench.sway.extract import extract_sway_events


def test_augmented_dump_has_sway_events() -> None:
    path = Path("data_exports/openai/chatgpt_convo_dump_augmented.json")
    assert path.exists(), "Augmented dump should exist for demo/testing"

    rows = json.loads(path.read_text(encoding="utf-8"))
    convos = load_manual_thread_dump(rows)

    candidates = extract_challenge_candidates(convos, min_score=0.25)
    events = extract_sway_events(convos)

    assert len(candidates) >= 8
    assert len(events) >= 8

