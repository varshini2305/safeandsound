"use client";

function escapeHtml(s: string) {
  return s.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

export function HighlightedText(props: { text: string; spans: Array<{ start: number; end: number; entity_type: string }> }) {
  const spans = [...props.spans].sort((a, b) => a.start - b.start);
  let cursor = 0;
  const parts: string[] = [];
  for (const sp of spans) {
    const start = Math.max(0, Math.min(props.text.length, sp.start));
    const end = Math.max(0, Math.min(props.text.length, sp.end));
    if (end <= start) continue;
    if (start > cursor) parts.push(escapeHtml(props.text.slice(cursor, start)));
    const inner = escapeHtml(props.text.slice(start, end));
    parts.push(
      `<mark title="${escapeHtml(sp.entity_type)}" style="background: rgba(99,102,241,0.35); border: 1px solid rgba(99,102,241,0.55); padding: 0 2px; border-radius: 6px;">${inner}</mark>`
    );
    cursor = end;
  }
  if (cursor < props.text.length) parts.push(escapeHtml(props.text.slice(cursor)));

  return (
    <pre
      className="whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-xs text-slate-200"
      dangerouslySetInnerHTML={{ __html: parts.join("") }}
    />
  );
}

export function PiiDiff(props: {
  role: string;
  originalLine: string;
  sanitizedLine: string;
  spans: Array<{ line_span_start: number; line_span_end: number; entity_type: string; replacement: string }>;
}) {
  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
      <div>
        <div className="mb-1 text-xs text-slate-400">Original ({props.role})</div>
        <HighlightedText
          text={props.originalLine}
          spans={props.spans.map((s) => ({ start: s.line_span_start, end: s.line_span_end, entity_type: s.entity_type }))}
        />
      </div>
      <div>
        <div className="mb-1 text-xs text-slate-400">Sanitized</div>
        <pre className="whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-xs text-slate-200">
          {props.sanitizedLine}
        </pre>
        <div className="mt-2 flex flex-wrap gap-2">
          {props.spans.slice(0, 12).map((s, i) => (
            <span key={i} className="pill">
              {s.entity_type} → {s.replacement}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
