"use client";

type Op = { t: "eq" | "ins" | "del"; w: string };

function diffWords(a: string, b: string): Op[] {
  const aw = (a ?? "").split(/\s+/).filter(Boolean);
  const bw = (b ?? "").split(/\s+/).filter(Boolean);
  const n = aw.length;
  const m = bw.length;
  const dp: number[][] = Array.from({ length: n + 1 }, () => Array(m + 1).fill(0));

  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] = aw[i] === bw[j] ? 1 + dp[i + 1][j + 1] : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }

  const ops: Op[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (aw[i] === bw[j]) {
      ops.push({ t: "eq", w: aw[i] });
      i++;
      j++;
      continue;
    }
    if (dp[i + 1][j] >= dp[i][j + 1]) {
      ops.push({ t: "del", w: aw[i] });
      i++;
    } else {
      ops.push({ t: "ins", w: bw[j] });
      j++;
    }
  }
  while (i < n) {
    ops.push({ t: "del", w: aw[i++] });
  }
  while (j < m) {
    ops.push({ t: "ins", w: bw[j++] });
  }
  return ops;
}

export function TextDiff(props: { before: string; after: string; maxOps?: number }) {
  const ops = diffWords(props.before, props.after);
  const trimmed = typeof props.maxOps === "number" && ops.length > props.maxOps ? ops.slice(0, props.maxOps) : ops;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/30 p-3 text-xs text-slate-200">
      <div className="mb-2 text-[11px] text-slate-400">
        Highlight: <span className="rounded bg-emerald-900/40 px-1">added</span>{" "}
        <span className="rounded bg-rose-900/40 px-1">removed</span>
      </div>
      <div className="flex flex-wrap gap-x-1 gap-y-1 leading-5">
        {trimmed.map((o, idx) => {
          const cls =
            o.t === "ins"
              ? "bg-emerald-900/40 text-emerald-100"
              : o.t === "del"
                ? "bg-rose-900/40 text-rose-100 line-through"
                : "text-slate-200";
          return (
            <span key={idx} className={`rounded px-1 ${cls}`}>
              {o.w}
            </span>
          );
        })}
      </div>
      {trimmed.length !== ops.length ? <div className="mt-2 text-[11px] text-slate-400">Diff truncated.</div> : null}
    </div>
  );
}

