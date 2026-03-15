import json
from pathlib import Path

from swaybench.io.claude_export import load_claude_export_from_path


def test_load_claude_sample():
    fixture = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "claude_export_sample"
        / "conversations.json"
    )
    convos = load_claude_export_from_path(fixture)
    assert len(convos) == 1
    assert convos[0].turns[0].role == "user"
    assert any("212-555-0199" in t.text for t in convos[0].turns)

