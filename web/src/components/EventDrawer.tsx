"use client";

import { useMemo, useState } from "react";
import { verifyWebBatch } from "@/lib/api";
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
  const [onlyBeliefShifts, setOnlyBeliefShifts] = useState(false);
  const [labels, setLabels] = useState<Record<string, any>>(() => (typeof window === "undefined" ? {} : loadLabels(props.analysisId)));
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [verifyErr, setVerifyErr] = useState<string | null>(null);
  const [showSignalDetails, setShowSignalDetails] = useState(false);
  const [verifyProvider, setVerifyProvider] = useState<"gemini" | "openai" | "both">("both");

  const isBeliefShift = (e: any) => {
    if (typeof e?.ui?.belief_shift === "boolean") return !!e.ui.belief_shift;
    const c = Number(e?.nli?.contradiction ?? 0);
    return c >= 0.6;
  };

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return props.events
      .filter((e) => (onlyUnsupported ? !e.evidence_flag : true))
      .filter((e) => (onlyBeliefShifts ? isBeliefShift(e) : true))
      .filter((e) => {
        if (!q) return true;
        const blob = `${e.user_question}\n${e.user_challenge}\n${e.a1_sanitized ?? ""}\n${e.a2_sanitized ?? ""}`.toLowerCase();
        return blob.includes(q);
      });
  }, [props.events, query, onlyUnsupported, onlyBeliefShifts]);

  const chatLabel = (e: any) => String(e.convo_label ?? "Chat");

  const selectedLabel = selected ? labels[selected.id]?.label ?? null : null;
  const selectedNotes = selected ? labels[selected.id]?.notes ?? "" : "";
  const selectedVerify = selected ? labels[selected.id]?.ai_verify ?? null : null;

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

  async function runWebVerifyBatchForRows() {
    setVerifyErr(null);
    const items = rows.slice(0, 10).map((e) => ({
      id: String(e.id),
      user_question: String(e.user_question ?? ""),
      a1: String(e.a1_sanitized ?? ""),
      a2: String(e.a2_sanitized ?? ""),
      user_challenge: String(e.user_challenge ?? "")
    }));
    if (!items.length) return;
    setVerifyLoading(true);
    try {
      const res = await verifyWebBatch({
        provider: verifyProvider,
        items,
        max_items: 10,
      });
      const next = { ...labels };
      for (const r of res.results ?? []) {
        const k = String(r.id);
        const entry = next[k] ?? {};
        const ai = entry.ai_verify ?? {};
        ai[String(r.provider)] = {
          model: r.model,
          update_answer_correctness: r.update_answer_correctness ?? null,
          checked_at: new Date().toISOString()
        };
        next[k] = { ...entry, ai_verify: ai, updated_at: new Date().toISOString() };
      }
      setLabels(next);
      saveLabels(props.analysisId, next);
    } catch (e: any) {
      setVerifyErr(e?.message ?? String(e));
    } finally {
      setVerifyLoading(false);
    }
  }

  async function runWebVerifySingle() {
    if (!selected) return;
    setVerifyErr(null);
    setVerifyLoading(true);
    try {
      const res = await verifyWebBatch({
        provider: verifyProvider,
        items: [
          {
            id: String(selected.id),
            user_question: String(selected.user_question ?? ""),
            a1: String(selected.a1_sanitized ?? ""),
            a2: String(selected.a2_sanitized ?? ""),
            user_challenge: String(selected.user_challenge ?? "")
          }
        ],
        max_items: 1
      });
      const next = { ...labels };
      for (const r of res.results ?? []) {
        const k = String(r.id);
        const entry = next[k] ?? {};
        const ai = entry.ai_verify ?? {};
        ai[String(r.provider)] = {
          model: r.model,
          update_answer_correctness: r.update_answer_correctness ?? null,
          checked_at: new Date().toISOString()
        };
        next[k] = { ...entry, ai_verify: ai, updated_at: new Date().toISOString() };
      }
      setLabels(next);
      saveLabels(props.analysisId, next);
    } catch (e: any) {
      setVerifyErr(e?.message ?? String(e));
    } finally {
      setVerifyLoading(false);
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
            <label
              className="flex items-center gap-2 text-sm text-slate-300"
              title="Requires local stance/NLI model. Filters to cases where A2 likely contradicts A1 (a stronger signal than paraphrasing)."
            >
              <input
                type="checkbox"
                checked={onlyBeliefShifts}
                onChange={(e) => setOnlyBeliefShifts(e.target.checked)}
              />
              Only belief shifts
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
            <button className="btn btn-ghost" onClick={runWebVerifyBatchForRows} disabled={verifyLoading}>
              {verifyLoading ? "Verifying…" : "Verify filtered with AI"}
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
                <th className="px-3 py-2 font-medium" title="Belief shift = likely contradiction between A1 and A2 (local stance/NLI model).">
                  Shift
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
                  <td className="px-3 py-2 text-slate-200">{isBeliefShift(e) ? "yes" : ""}</td>
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
                  <td className="px-3 py-4 text-slate-400" colSpan={6}>
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
                  {selected.nli ? (
                    <div className="flex flex-wrap gap-2 text-xs text-slate-300">
                      <span className="pill">NLI entail: {Number(selected.nli.entailment ?? 0).toFixed(2)}</span>
                      <span className="pill">NLI neutral: {Number(selected.nli.neutral ?? 0).toFixed(2)}</span>
                      <span className="pill">NLI contradict: {Number(selected.nli.contradiction ?? 0).toFixed(2)}</span>
                      <span className="pill">belief shift: {isBeliefShift(selected) ? "yes" : "no"}</span>
                    </div>
                  ) : (
                    <div className="text-[11px] text-slate-400">
                      No local stance/NLI result for this event (install `requirements-ml.txt` and enable the toggle).
                    </div>
                  )}
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
              <div className="mb-2 text-xs font-semibold text-slate-200">Verify with AI (optional)</div>
              <div className="text-xs text-slate-400">
                Sends the currently displayed <span className="font-mono">anonymized</span> snippet to a verifier. Returns only:
                <span className="font-mono"> update_answer_correctness = TRUE/FALSE</span>.
              </div>
              <div className="mt-2 grid grid-cols-1 gap-2">
                <label className="text-xs text-slate-400">
                  Provider
                  <select className="input mt-1" value={verifyProvider} onChange={(e) => setVerifyProvider(e.target.value as any)}>
                    <option value="both">Gemini + OpenAI</option>
                    <option value="gemini">Gemini (grounded web search)</option>
                    <option value="openai">OpenAI (web search)</option>
                  </select>
                </label>
                <button className="btn btn-ghost" onClick={runWebVerifySingle} disabled={verifyLoading}>
                  {verifyLoading ? "Verifying…" : "Verify with AI"}
                </button>
                {verifyErr ? (
                  <pre className="whitespace-pre-wrap rounded-xl border border-red-900/50 bg-red-950/40 p-2 text-[11px] text-red-200">
                    {verifyErr}
                  </pre>
                ) : null}
                {selectedVerify ? (
                  <pre className="whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-950/50 p-2 text-[11px] text-slate-200">
                    {JSON.stringify(selectedVerify, null, 2)}
                  </pre>
                ) : (
                  <div className="text-[11px] text-slate-400">No AI verification run for this event yet.</div>
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
