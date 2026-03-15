from __future__ import annotations

import json
from typing import Iterable


def jsonl_dumps_bytes(rows: Iterable[dict]) -> bytes:
    lines = [json.dumps(r, ensure_ascii=False) for r in rows]
    return ("\n".join(lines) + "\n").encode("utf-8")


