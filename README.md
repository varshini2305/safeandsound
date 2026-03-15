# SwayBench

Local-first privacy + sycophancy analysis from chat exports.

## What this is

SwayBench is a local-first tool that:

1. Ingests a ChatGPT or Claude export
2. Detects and anonymizes sensitive data locally (PII + secrets like API keys)
3. Finds “pushback” moments (where the user challenges the assistant)
4. Ranks potential sycophancy cases (answer changes after unsupported pushback)
5. Lets you label correctness and export an anonymized JSONL dataset

## Quickstart (Next.js UI)

Backend:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-ml.txt   # optional: local ML (PII HF model + stance/NLI model)
pip install -e .
uvicorn server.main:app --reload --port 8000
```

Frontend:

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:3000`.

### UI flow (what you’ll do)

1) Privacy scan + anonymize  
2) Review/select “pushback” moments  
3) Review “Potential sycophancy” cases (answer changes after pushback)

### Defaults for fast demo

- The “Use default local dump” button reads `SWAYBENCH_DEFAULT_INPUT_PATH`.
- This repo includes an augmented manual-style dump for demo purposes:
  - `/Users/varshinibalaji/ds_projects/safeandsound/data_exports/openai/chatgpt_convo_dump_augmented.json`
  - Regenerate it: `python scripts/augment_demo_dump.py`

## Scoring (transparent heuristics)

SwayBench ranks cases with a simple heuristic (shown in the UI) combining:

- **Apology/acceptance** language in the assistant reply
- **Resistance** language (asking for evidence / reaffirming)
- **Change** between the assistant’s answers (A1 vs A2)
- Downweights the score when the user pushback includes evidence (links/quotes/citation-like cues)

## Manual correctness labeling (local)

- In the Sway Events panel, you can label each event as `correct` / `incorrect` / `unsure` and add notes.
- Labels are stored in the browser `localStorage` and can be downloaded as JSON.

## Optional: stance-shift model (local)

If `transformers` + `torch` are installed, you can enable a small NLI stance model to help distinguish:
- paraphrase/extra detail vs
- true contradiction / belief shift

This is optional and runs locally.

## Optional external verification (Gemini)

- UI supports an opt-in Gemini check that sends the **anonymized** A1/A2 snippet to the backend, which calls Gemini.
- Set server-side env var (recommended) or paste a key in the UI:
  - `SWAYBENCH_GEMINI_API_KEY=...`
  - Optional: `SWAYBENCH_GEMINI_MODEL=gemini-1.5-flash`

## Streamlit UI (legacy)

```bash
python -m streamlit run app.py
```

The Streamlit UI is kept for quick iteration; the Next.js UI is the main demo.

## Optional: Inspect AI eval

Inspect is optional. If you want to run the 2-step “flip-under-pushback” eval:

```bash
pip install -r requirements-inspect.txt
python -m swaybench.eval.run_inspect --dataset /path/to/swaybench.jsonl --model <your-model>
```

You’ll also need the relevant provider env vars (e.g., API keys) for your chosen model backend.

## CLI (dataset export)

```bash
pip install -e .
python -m swaybench.cli --zip /path/to/chatgpt-export.zip --out swaybench.jsonl --salt my-salt
```

## Export format

Each JSONL line is one sway event with fields:

`id, convo_id, topic_cluster_id, user_question, user_challenge, evidence_flag, a1_sanitized, a2_sanitized, pii_stats, timestamps`
