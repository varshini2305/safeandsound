import json
import zipfile
from pathlib import Path

from swaybench.io.chatgpt_export import load_chatgpt_export


def test_load_from_fixture_json():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "fake_export" / "conversations.json"
    raw = json.loads(fixture.read_text(encoding="utf-8"))
    convos = load_chatgpt_export(raw)
    assert len(convos) >= 2
    assert convos[0].turns[0].role == "user"
    assert any("alice@example.com" in t.text for t in convos[0].turns)


def test_load_from_zip_bytes(tmp_path):
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "fake_export" / "conversations.json"
    raw = fixture.read_text(encoding="utf-8")
    zpath = tmp_path / "export.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("conversations.json", raw)
    convos = load_chatgpt_export(zpath.read_bytes())
    assert len(convos) >= 1

