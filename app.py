import json
import subprocess
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from swaybench.io.chatgpt_export import load_chatgpt_export
from swaybench.io.claude_export import load_claude_export_from_path
from swaybench.pii.anonymize import AnonymizationConfig, anonymize_conversations
from swaybench.sway.cluster import assign_topic_clusters
from swaybench.sway.extract import extract_sway_events
from swaybench.eval.replay import replay_metrics
from swaybench.util.jsonl import jsonl_dumps_bytes


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "fake_export" / "conversations.json"


def _load_fixture() -> list[dict[str, Any]]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


st.set_page_config(page_title="SwayBench", layout="wide")

st.title("SwayBench")
st.caption(
    "Local-first PII anonymization + extraction of unsupported-disagreement → assistant flip/concession episodes."
)

with st.sidebar:
    st.header("Input")
    input_mode = st.selectbox(
        "Input type",
        ["Synthetic sample", "ChatGPT export (.zip)", "Claude export (local path)"],
        index=0,
    )
    uploaded = None
    claude_path = ""
    if input_mode == "ChatGPT export (.zip)":
        uploaded = st.file_uploader("Upload ChatGPT export (.zip)", type=["zip"])
    elif input_mode == "Claude export (local path)":
        claude_path = st.text_input(
            "Claude export folder or conversations.json",
            value="/Users/varshinibalaji/ds_projects/safeandsound/data_exports/claude/data-2026-03-15-04-44-46-batch-0000",
        )

    st.header("Anonymization")
    salt = st.text_input("Salt (keeps replacements consistent)", value="demo-salt")
    mode = st.selectbox(
        "Anonymization style",
        ["synthetic", "placeholder"],
        index=0,
        help="Synthetic replaces PII with realistic fake values; placeholder uses <TYPE_N> tokens.",
    )
    redact_urls = st.checkbox("Treat URLs as sensitive", value=False)
    enable_presidio = st.checkbox("Enable Presidio (if installed)", value=False)

    st.header("Export")
    minimal_export = st.checkbox("Minimal export (omit assistant turns)", value=False)

    st.header("Inspect AI (optional)")
    model_name = st.text_input("Model", value="")


if input_mode == "Synthetic sample":
    raw_conversations = _load_fixture()
    conversations = load_chatgpt_export(raw_conversations)
elif input_mode == "ChatGPT export (.zip)":
    if uploaded is None:
        st.info("Upload a ChatGPT export `.zip` (it should contain `conversations.json`).")
        st.stop()
    conversations = load_chatgpt_export(uploaded.getvalue())
else:
    if not claude_path.strip():
        st.info("Provide a Claude export folder path (containing `conversations.json`) or a direct `conversations.json` path.")
        st.stop()
    conversations = load_claude_export_from_path(claude_path.strip())
    if not conversations:
        st.error("Could not parse Claude export at that path.")
        st.stop()

st.subheader("1) Parsed conversations")
st.write(f"Conversations: {len(conversations)}")

preview_rows = []
for c in conversations[:20]:
    preview_rows.append(
        {
            "conversation_id": c.conversation_id,
            "title": c.title,
            "turns": len(c.turns),
            "create_time": c.create_time,
        }
    )
st.dataframe(pd.DataFrame(preview_rows), use_container_width=True)


st.subheader("2) PII detection + anonymization (local)")
anon_cfg = AnonymizationConfig(
    salt=salt,
    redact_urls=redact_urls,
    enable_presidio=enable_presidio,
    mode=mode,
)

sanitized_conversations, pii_summary = anonymize_conversations(conversations, anon_cfg)

pii_df = pd.DataFrame(
    [{"entity_type": k, "count": v} for k, v in sorted(pii_summary.entity_counts.items())]
)
col1, col2 = st.columns([1, 2])
with col1:
    st.metric("Total detected spans", pii_summary.total_spans)
    st.dataframe(pii_df, use_container_width=True, hide_index=True)
with col2:
    st.write("Top conversations by detected sensitive spans")
    top_df = pd.DataFrame(pii_summary.top_conversations)
    if len(top_df) == 0:
        st.write("(none)")
    else:
        st.dataframe(top_df, use_container_width=True, hide_index=True)

sanitized_bundle = {
    "conversations": [asdict(c) for c in sanitized_conversations],
    "pii_summary": pii_summary.model_dump(),
}
st.download_button(
    "Download sanitized bundle (JSON)",
    data=json.dumps(sanitized_bundle, indent=2).encode("utf-8"),
    file_name="swaybench_sanitized_bundle.json",
    mime="application/json",
)


st.subheader("3) Extract sway events")
events = extract_sway_events(sanitized_conversations)
events = assign_topic_clusters(events)

st.write(f"Extracted sway events: {len(events)}")

if len(events) == 0:
    st.warning("No sway events found in this dataset with current heuristics.")
    st.stop()

events_df = pd.DataFrame([e.to_row() for e in events])
st.dataframe(
    events_df.drop(columns=["a1_sanitized", "a2_sanitized"], errors="ignore"),
    use_container_width=True,
    hide_index=True,
)

st.write("Top events (expand to view)")
for e in events[:25]:
    with st.expander(
        f"[{e.flip_likelihood:.2f}] {e.conversation_title or e.convo_id} — cluster {e.topic_cluster_id} — supported={e.evidence_flag}"
    ):
        st.markdown("**User question**")
        st.write(e.user_question)
        st.markdown("**Assistant (before)**")
        st.write(e.a1_sanitized)
        st.markdown("**User challenge**")
        st.write(e.user_challenge)
        st.markdown("**Assistant (after)**")
        st.write(e.a2_sanitized)


st.subheader("4) Export SwayBench JSONL (opt-in)")
jsonl_bytes = jsonl_dumps_bytes([e.to_json(minimal=minimal_export) for e in events])
st.download_button(
    "Download SwayBench JSONL",
    data=jsonl_bytes,
    file_name="swaybench.jsonl",
    mime="application/jsonl",
)


st.subheader("5) Metrics (replay + optional Inspect)")
rm = replay_metrics(events)
st.write("Replay metrics (computed from extracted A1/A2 pairs)")
st.json(rm)

if model_name.strip():
    st.write("Inspect AI run (optional, requires `inspect-ai` and a configured provider).")
    if st.button("Run Inspect eval now"):
        with tempfile.TemporaryDirectory() as td:
            dataset_path = Path(td) / "swaybench.jsonl"
            dataset_path.write_bytes(jsonl_bytes)
            cmd = [
                "python",
                "-m",
                "swaybench.eval.run_inspect",
                "--dataset",
                str(dataset_path),
                "--model",
                model_name.strip(),
            ]
            try:
                proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
                if proc.returncode != 0:
                    st.error("Inspect run failed.")
                    st.code(proc.stderr or proc.stdout)
                else:
                    st.success("Inspect run complete.")
                    st.json(json.loads(proc.stdout))
            except FileNotFoundError:
                st.error("Python not found in PATH for subprocess invocation.")
else:
    st.info("To run Inspect eval, enter a model name in the sidebar.")
