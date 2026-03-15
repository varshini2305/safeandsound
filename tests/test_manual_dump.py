import json
from pathlib import Path

from swaybench.io.auto import load_any_export


def test_auto_load_manual_dump_json():
    raw = Path("fixtures/manual_dump_sample.json").read_bytes()
    res = load_any_export(raw)
    assert res.detected_format == "chatgpt"
    assert res.upload_kind == "json"
    assert len(res.conversations) == 1
    assert res.conversations[0].turns[0].role == "user"

