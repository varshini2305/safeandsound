# Safe and Sound

Local-first privacy + sycophancy analysis from chat exports, with a user-friendly dashboard to build a real-world benchmark.

**Naming:** The product is **Safe and Sound**. Any benchmark dataset exported/shared from the dashboard should be referred to as the **Safe and Sound benchmark** (the codebase still contains internal modules named `swaybench` from early prototyping).

## What this is

Safe and Sound is a local-first tool that:

1. Ingests a ChatGPT or Claude export
2. Detects and anonymizes sensitive data locally (PII + secrets like API keys)
3. Finds “pushback” moments (where the user challenges the assistant)
4. Ranks potential sycophancy cases (answer changes after unsupported pushback)
5. Lets you label correctness and export an anonymized JSONL dataset (the Safe and Sound benchmark)

## Methodology (high level)

### 1) Local-first privacy scan + anonymization

- The raw export is processed **on-device** (in the browser) when “Process locally in your browser (no upload)” is enabled.
- Sensitive content is detected (regex-first, optional local ML) and replaced with anonymized placeholders or deterministic synthetic values.
- After anonymization, downstream analysis and optional sharing are safe-by-design: **only anonymized snippets** are used for later steps.

### 2) Candidate mining: “pushback moments”

- The system scans for user turns that look like disagreement/challenge (phrase-based cues like “that’s wrong”, “are you sure?”, leading “but”, etc.).
- Users can review and select which pushback moments should be included for sycophancy analysis.

### 3) Sycophancy analysis: “answer changes after pushback”

- For each selected moment, Safe and Sound compares the assistant’s response before vs after pushback, and ranks cases with transparent heuristics.
- Optional: a lightweight local stance/NLI model can help distinguish paraphrase from contradiction (“belief shift”).

### 4) Verification & labeling

- Manual labeling (`correct` / `incorrect` / `unsure`) is supported in the UI and exported as JSON.
- Optional web-backed verification can be run on **anonymized snippets** via Gemini or OpenAI (user chooses provider).

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

### Local-first deployment note

To keep uploads truly local-first when you host the site, enable **“Process locally in your browser (no upload)”** in the UI.

- In that mode, the **raw export never leaves the user’s device**.
- After anonymization, it’s acceptable to upload/process **anonymized** artifacts server-side (e.g., for sharing benchmark items), since the sensitive content has been removed.
- The backend is only needed for optional external verification on anonymized snippets and for any server-side sharing workflows you add later.

## Vercel deployment

This repo is Vercel-friendly as a Next.js app. The recommended production mode is:

- **Client-side local-first analysis** (no upload of raw exports)
- **Serverless API routes** for optional verification and for sharing anonymized benchmark items

### Environment variables (Vercel)

Set these in your Vercel project settings:

- `MONGODB_URI` (required for sharing)
- `MONGODB_DB=ai_safety` (optional; defaults to `ai_safety`)
- `MONGODB_COLLECTION=SwayBench` (optional; defaults to `SwayBench`)
- `GEMINI_API_KEY` (optional; for Gemini grounded search verification)
- `OPENAI_API_KEY` (optional; for OpenAI web search verification)
- Optional model overrides:
  - `GEMINI_MODEL` (default `gemini-2.0-flash`)
  - `SWAYBENCH_OPENAI_MODEL` (default `gpt-4o-mini`)

### What gets uploaded

- Raw exports: **never uploaded** when local-first mode is enabled.
- Shared dataset: only **anonymized benchmark items** are uploaded (opt-in button in the UI).

## Troubleshooting

- **Next dev error: `Cannot find module './###.js'`**
  - This is usually a stale/corrupted Next.js dev cache.
  - Fix:
    ```bash
    cd web
    npm run clean
    npm run dev
    ```

### Defaults for fast demo

- The “Use default local dump” button reads `SWAYBENCH_DEFAULT_INPUT_PATH`.
- This repo includes an augmented manual-style dump for demo purposes:
  - `/Users/varshinibalaji/ds_projects/safeandsound/data_exports/openai/chatgpt_convo_dump_augmented.json`
  - Regenerate it: `python scripts/augment_demo_dump.py`

## Scoring (transparent heuristics)

Safe and Sound ranks cases with a simple heuristic (shown in the UI) combining:

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
  - `.env`: `GEMINI_API_KEY=...` (or `SWAYBENCH_GEMINI_API_KEY=...`)
  - Optional: `GEMINI_MODEL=gemini-1.5-flash` (or `SWAYBENCH_GEMINI_MODEL=...`)

## Optional external verification (OpenAI web search)

- If you set `.env` `OPENAI_API_KEY=...`, SwayBench can also verify cases using OpenAI’s web search tool (Responses API).
- The UI lets you choose `Gemini`, `OpenAI`, or `Both` for verification.

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

Each JSONL line is one benchmark item (“sway event”) with fields:

`id, convo_id, topic_cluster_id, user_question, user_challenge, evidence_flag, a1_sanitized, a2_sanitized, pii_stats, timestamps`

## Tech stack

- **Frontend:** Next.js (React) + TypeScript + Tailwind CSS
- **Backend:** Python + FastAPI + Uvicorn + Pydantic
- **Local ML (optional):** Hugging Face `transformers` + `torch` (PII token classifier; stance/NLI model)
- **Clustering:** scikit-learn
- **Testing:** pytest

## Challenges (hackathon notes)

- **ChatGPT export latency:** ChatGPT exports can take significant time to arrive. To unblock development and demo, the repo includes an augmented sample dump created by extending available conversations.
- **Export format variability:** Different assistants export data differently (ChatGPT graph vs Claude JSON vs manual dumps), so ingestion was made format-flexible.
- **Verification without cost:** High-quality correctness verification without paid APIs is non-trivial; Safe and Sound defaults to local heuristics + optional local stance models, with opt-in web-backed verification on anonymized snippets.
