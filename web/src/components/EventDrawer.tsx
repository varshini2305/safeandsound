"use client";

import { useMemo, useState } from "react";
import { verifyGemini } from "@/lib/api";
import { TextDiff } from "@/components/TextDiff";

type LabelValue = "correct" | "incorrect" | "unsure";

function loadLabels(analysisId: string): Record<string, any> {
  try {
    const raw = localStorage.getItem(`swaybench:labels:${analysisId}`);
    return raw ? (JSON.parse(raw) as any) : {};
  } catch {
    return {};
  }
}

function saveLabels(analysisId: string, labels: Record<string, any>) {
  localStorage.setItem(`swaybench:labels:${analysisId}`, JSON.stringify(labels));
}

function downloadJson(filename: string, obj: any) {
  const blob = new Blob([JSON.stringify(obj, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function EventDrawer(props: { events: any[]; analysisId: string }) {
  const [selected, setSelected] = useState<any | null>(null);
  const [query, setQuery] = useState("");
  const [onlyUnsupported, setOnlyUnsupported] = useState(true);
  const [labels, setLabels] = useState<Record<string, any>>(() => (typeof window === "undefined" ? {} : loadLabels(props.analysisId)));
  const [geminiKey, setGeminiKey] = useState("");
  const [geminiModel, setGeminiModel] = useState("gemini-1.5-flash");
  const [geminiLoading, setGeminiLoading] = useState(false);
  const [geminiErr, setGeminiErr] = useState<string | null>(null);
  const [showSignalDetails, setShowSignalDetails] = useState(false);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return props.events
      .filter((e) => (onlyUnsupported ? !e.evidence_flag : true))
      .filter((e) => {
        if (!q) return true;
        const blob = `${e.user_question}\n${e.user_challenge}\n${e.a1_sanitized ?? ""}\n${e.a2_sanitized ?? ""}`.toLowerCase();
        return blob.includes(q);
      });
  }, [props.events, query, onlyUnsupported]);

  const chatLabel = (e: any) => String(e.convo_label ?? "Chat");

  const selectedLabel = selected ? labels[selected.id]?.label ?? null : null;
  const selectedNotes = selected ? labels[selected.id]?.notes ?? "" : "";
  const selectedGemini = selected ? labels[selected.id]?.gemini ?? null : null;

  function setSelectedLabel(label: LabelValue) {
    if (!selected) return;
    const next = {
      ...labels,
      [selected.id]: {
        ...(labels[selected.id] ?? {}),
        label,
        updated_at: new Date().toISOString()
      }
    };
    setLabels(next);
    saveLabels(props.analysisId, next);
  }

  function setSelectedNotes(notes: string) {
    if (!selected) return;
    const next = {
      ...labels,
      [selected.id]: {
        ...(labels[selected.id] ?? {}),
        notes,
        updated_at: new Date().toISOString()
      }
    };
    setLabels(next);
    saveLabels(props.analysisId, next);
  }

  const labeledCount = Object.values(labels).filter((v: any) => v?.label).length;

  async function runGemini() {
    if (!selected) return;
    setGeminiErr(null);
    if (!geminiKey.trim()) {
      setGeminiErr("Paste a Gemini API key first (kept in your browser; not stored on disk).");
      return;
    }
    setGeminiLoading(true);
    try {
      const res = await verifyGemini({
        user_question: String(selected.user_question ?? ""),
        a1: String(selected.a1_sanitized ?? ""),
        a2: String(selected.a2_sanitized ?? ""),
        user_challenge: String(selected.user_challenge ?? ""),
        api_key: geminiKey.trim(),
        model: geminiModel.trim()
      });
      const next = {
        ...labels,
        [selected.id]: {
          ...(labels[selected.id] ?? {}),
          gemini: { model: res.model, raw: res.raw, checked_at: new Date().toISOString() },
          updated_at: new Date().toISOString()
        }
      };
      setLabels(next);
      saveLabels(props.analysisId, next);
    } catch (e: any) {
      setGeminiErr(e?.message ?? String(e));
    } finally {
      setGeminiLoading(false);
    }
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <div className="card p-4 lg:col-span-2">
        <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <input
              className="input"
              placeholder="Search events…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" checked={onlyUnsupported} onChange={(e) => setOnlyUnsupported(e.target.checked)} />
              Only unsupported
            </label>
            <span className="pill text-xs text-slate-300">labeled: {labeledCount}</span>
            <button
              className="btn btn-ghost"
              onClick={() =>
                downloadJson(`swaybench_labels_${props.analysisId}.json`, {
                  analysis_id: props.analysisId,
                  created_at: new Date().toISOString(),
                  labels
                })
              }
            >
              Download labels
            </button>
          </div>
        </div>
        <div className="overflow-auto rounded-xl border border-slate-800">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-900/60 text-xs uppercase text-slate-400">
              <tr>
                <th
                  className="px-3 py-2 font-medium"
                  title="Gullibility score: higher means the assistant likely conceded and changed its answer after pushback."
                >
                  Gullibility
                </th>
                <th className="px-3 py-2 font-medium">Label</th>
                <th className="px-3 py-2 font-medium">Chat</th>
                <th className="px-3 py-2 font-medium">Question</th>
                <th className="px-3 py-2 font-medium">Challenge</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((e) => (
                <tr
                  key={e.id}
                  className="cursor-pointer border-t border-slate-800 hover:bg-slate-900/30"
                  onClick={() => setSelected(e)}
                >
                  <td className="px-3 py-2 font-mono text-slate-200">{Number(e.signals?.flip_likelihood ?? 0).toFixed(2)}</td>
                  <td className="px-3 py-2 text-slate-200">{String(labels[e.id]?.label ?? "")}</td>
                  <td className="px-3 py-2 text-slate-200">
                    <span className="pill">{chatLabel(e)}</span>
                  </td>
                  <td className="px-3 py-2 text-slate-200">{String(e.user_question ?? "").slice(0, 120)}</td>
                  <td className="px-3 py-2 text-slate-200">{String(e.user_challenge ?? "").slice(0, 120)}</td>
                </tr>
              ))}
              {rows.length === 0 ? (
                <tr>
                  <td className="px-3 py-4 text-slate-400" colSpan={5}>
                    No matching events.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card p-4">
        <div className="mb-2 text-sm font-semibold">Event details</div>
        {selected ? (
          <div className="flex flex-col gap-3 text-sm">
            <div className="flex flex-wrap gap-2">
              <span className="pill">id: {selected.id}</span>
              <span className="pill">supported: {String(!!selected.evidence_flag)}</span>
              <span className="pill">{chatLabel(selected)}</span>
              <span className="pill">gullibility: {Number(selected.signals?.flip_likelihood ?? 0).toFixed(2)}</span>
              <span className="pill">
                change: {(1 - Number(selected.signals?.similarity_a1_a2 ?? 0)).toFixed(2)}
              </span>
              <button className="btn btn-ghost" onClick={() => setShowSignalDetails((v) => !v)}>
                {showSignalDetails ? "Hide scoring details" : "Show scoring details"}
              </button>
            </div>

            {selected.ui?.headline ? (
              <div className="rounded-xl border border-slate-800 bg-slate-950/30 p-3 text-sm text-slate-200">
                <div className="text-xs font-semibold text-slate-200">What happened</div>
                <div className="mt-1 text-sm text-slate-300">{String(selected.ui.headline)}</div>
                {selected.ui.note ? <div className="mt-1 text-xs text-slate-400">{String(selected.ui.note)}</div> : null}
              </div>
            ) : null}

            {showSignalDetails ? (
              <div className="rounded-xl border border-slate-800 bg-slate-950/30 p-3 text-xs text-slate-200">
                <div className="text-xs font-semibold text-slate-200">Scoring signals (debuggable)</div>
                <div className="mt-2 grid grid-cols-1 gap-2">
                  <div className="flex flex-wrap gap-2 text-xs text-slate-300">
                    <span className="pill">apology/acceptance: {Number(selected.signals?.concession ?? 0).toFixed(2)}</span>
                    <span className="pill">resistance: {Number(selected.signals?.resistance ?? 0).toFixed(2)}</span>
                    <span className="pill">change: {(1 - Number(selected.signals?.similarity_a1_a2 ?? 0)).toFixed(2)}</span>
                  </div>
                  <pre className="whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-950/50 p-2 text-[11px] text-slate-200">
                    {JSON.stringify(selected.signals ?? {}, null, 2)}
                  </pre>
                </div>
              </div>
            ) : null}

            <div className="rounded-xl border border-slate-800 bg-slate-950/30 p-3">
              <div className="mb-2 text-xs font-semibold text-slate-200">Manual correctness label</div>
              <div className="flex flex-wrap gap-2">
                <button
                  className={`btn ${selectedLabel === "correct" ? "btn-primary" : "btn-ghost"}`}
                  onClick={() => setSelectedLabel("correct")}
                >
                  Correct change
                </button>
                <button
                  className={`btn ${selectedLabel === "incorrect" ? "btn-primary" : "btn-ghost"}`}
                  onClick={() => setSelectedLabel("incorrect")}
                >
                  Incorrect change
                </button>
                <button
                  className={`btn ${selectedLabel === "unsure" ? "btn-primary" : "btn-ghost"}`}
                  onClick={() => setSelectedLabel("unsure")}
                >
                  Unsure
                </button>
              </div>
              <label className="mt-3 block text-xs text-slate-400">
                Notes (optional)
                <textarea
                  className="input mt-1 h-20 w-full"
                  value={selectedNotes}
                  onChange={(e) => setSelectedNotes(e.target.value)}
                  placeholder="Why is the change correct/incorrect? Any evidence you checked?"
                />
              </label>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-950/30 p-3">
              <div className="mb-2 text-xs font-semibold text-slate-200">External verification (Gemini, optional)</div>
              <div className="text-xs text-slate-400">
                Sends the currently displayed <span className="font-mono">anonymized</span> A1/A2 snippet to Gemini for a judgment.
              </div>
              <div className="mt-2 grid grid-cols-1 gap-2">
                <label className="text-xs text-slate-400">
                  Gemini API key
                  <input
                    className="input mt-1"
                    value={geminiKey}
                    onChange={(e) => setGeminiKey(e.target.value)}
                    placeholder="AIza…"
                    type="password"
                  />
                </label>
                <label className="text-xs text-slate-400">
                  Model
                  <input className="input mt-1" value={geminiModel} onChange={(e) => setGeminiModel(e.target.value)} />
                </label>
                <button className="btn btn-ghost" onClick={runGemini} disabled={geminiLoading}>
                  {geminiLoading ? "Checking…" : "Run Gemini check"}
                </button>
                {geminiErr ? (
                  <pre className="whitespace-pre-wrap rounded-xl border border-red-900/50 bg-red-950/40 p-2 text-[11px] text-red-200">
                    {geminiErr}
                  </pre>
                ) : null}
                {selectedGemini ? (
                  <pre className="whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-950/50 p-2 text-[11px] text-slate-200">
                    {selectedGemini.raw}
                  </pre>
                ) : (
                  <div className="text-[11px] text-slate-400">No external check run for this event yet.</div>
                )}
              </div>
            </div>

            <div>
              <div className="text-xs text-slate-400">User question</div>
              <pre className="mt-1 whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-slate-200">
                {String(selected.user_question ?? "")}
              </pre>
            </div>
            <div>
              <div className="text-xs text-slate-400">Assistant (before)</div>
              <pre className="mt-1 whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-slate-200">
                {String(selected.a1_sanitized ?? "")}
              </pre>
            </div>
            <div>
              <div className="text-xs text-slate-400">User challenge</div>
              <pre className="mt-1 whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-slate-200">
                {String(selected.user_challenge ?? "")}
              </pre>
            </div>
            <div>
              <div className="text-xs text-slate-400">Assistant (after)</div>
              <pre className="mt-1 whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-slate-200">
                {String(selected.a2_sanitized ?? "")}
              </pre>
            </div>
            <div>
              <div className="text-xs text-slate-400">What changed (highlight)</div>
              <TextDiff before={String(selected.a1_sanitized ?? "")} after={String(selected.a2_sanitized ?? "")} maxOps={700} />
            </div>
          </div>
        ) : (
          <div className="text-sm text-slate-400">Select an event to inspect the A1→U→A2 window.</div>
        )}
      </div>
    </div>
  );
}
