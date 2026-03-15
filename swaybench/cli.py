from __future__ import annotations

import argparse
import json
from pathlib import Path

from swaybench.eval.replay import replay_metrics
from swaybench.io.chatgpt_export import load_chatgpt_export
from swaybench.io.claude_export import load_claude_export_from_path
from swaybench.pii.anonymize import AnonymizationConfig, anonymize_conversations
from swaybench.sway.cluster import assign_topic_clusters
from swaybench.sway.extract import extract_sway_events
from swaybench.util.jsonl import jsonl_dumps_bytes


def main() -> None:
    ap = argparse.ArgumentParser(prog="swaybench")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--zip", dest="zip_path", help="Path to ChatGPT export .zip")
    src.add_argument("--claude", dest="claude_path", help="Path to Claude export folder or conversations.json")
    ap.add_argument("--out", dest="out_path", required=True, help="Output JSONL path")
    ap.add_argument("--salt", default="swaybench", help="Salt for deterministic placeholders")
    ap.add_argument(
        "--mode",
        choices=["placeholder", "synthetic"],
        default="placeholder",
        help="Anonymization style: placeholder (<TYPE_N>) or synthetic fake values",
    )
    ap.add_argument("--redact-urls", action="store_true", help="Treat URLs as sensitive")
    ap.add_argument("--enable-presidio", action="store_true", help="Enable Presidio if installed")
    ap.add_argument("--minimal", action="store_true", help="Omit assistant turns in export")
    args = ap.parse_args()

    if args.zip_path:
        convos = load_chatgpt_export(Path(args.zip_path).read_bytes())
    else:
        convos = load_claude_export_from_path(args.claude_path)
    convos, pii_summary = anonymize_conversations(
        convos,
        AnonymizationConfig(
            salt=args.salt,
            redact_urls=args.redact_urls,
            enable_presidio=args.enable_presidio,
            mode=args.mode,
        ),
    )
    events = assign_topic_clusters(extract_sway_events(convos))
    out = Path(args.out_path)
    out.write_bytes(jsonl_dumps_bytes([e.to_json(minimal=args.minimal) for e in events]))

    metrics = replay_metrics(events)
    bundle_path = out.with_suffix(".sanitized_summary.json")
    bundle_path.write_text(json.dumps({"pii_summary": pii_summary.model_dump(), "replay_metrics": metrics}, indent=2))

    print(f"Wrote {len(events)} events to {out}")
    print(f"Wrote summary to {bundle_path}")


if __name__ == "__main__":
    main()
