export type InputType = "local" | "auto" | "chatgpt_zip" | "chatgpt_conversations_json" | "claude_conversations_json";

export type AnalyzeResponse = {
  analysis_id: string;
  input_type: InputType;
  structure_report: Record<string, any>;
  conversation_labels?: Record<string, string>;
  conversations_preview: Array<{
    conversation_id: string;
    title: string | null;
    create_time: number | null;
    turns: number;
    label?: string | null;
  }>;
  pii_summary: {
    total_spans: number;
    entity_counts: Record<string, number>;
    top_conversations: Array<{ conversation_id: string; title?: string | null; detected_spans: number }>;
  };
  pii_preview: null | {
    conversations: Array<{
      conversation_id: string;
      title: string | null;
      turns: Array<{
        role: string;
        original_line: string;
        sanitized_line: string;
        spans: Array<{
          start: number;
          end: number;
          entity_type: string;
          original: string;
          replacement: string;
          line_no: number;
          original_line: string;
          sanitized_line: string;
          line_span_start: number;
          line_span_end: number;
        }>;
      }>;
    }>;
  };
  challenge_candidates: Array<{
    id: string;
    convo_id: string;
    convo_label?: string | null;
    title: string | null;
    a1: string;
    user_challenge: string;
    a2: string | null;
    challenge_score: number;
    reasons: string[];
    assistant_was_question: boolean;
    turn_indices: Record<string, number>;
    passed_threshold?: boolean;
    chain_id?: string;
    chain_depth?: number;
    evidence?: boolean;
    signals?: {
      concession: number;
      resistance: number;
      stance_change: number;
      flip_likelihood: number;
    };
    context_window?: {
      radius: number;
      turns: Array<{ idx: number; role: string; text: string; time: number | null }>;
    };
    constraints?: {
      word_limit: number | null;
      char_limit: number | null;
      relevant_only: boolean;
      soft_concise: boolean;
      sources?: Array<Record<string, any>>;
    };
    followups?: {
      max_assistants: number;
      assistant_turns: Array<{
        idx: number;
        role: string;
        time: number | null;
        word_count: number;
        char_count: number;
        signals: Record<string, number>;
        constraint_violations: Array<Record<string, any>>;
        text: string;
      }>;
      immediate_a2_text: string | null;
      best_followup: { idx: number | null; flip_likelihood: number; stance_change: number; concession: number };
      first_concession_idx: number | null;
      a1_idx: number;
      challenge_idx: number;
    };
  }>;
  challenge_candidates_total: number;
  candidate_min_score_effective: number;
  disagreement_diagnostics: Record<string, any>;
  events: Array<any>;
  replay_metrics: Record<string, any>;
  download: { jsonl: string; sanitized_bundle: string };
  export_jsonl_base64: string;
  export_jsonl_truncated: boolean;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

export async function analyze(form: FormData): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE}/api/analyze`, { method: "POST", body: form });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return (await res.json()) as AnalyzeResponse;
}

export async function analyzeDefault(form: FormData): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE}/api/analyze_default`, { method: "POST", body: form });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return (await res.json()) as AnalyzeResponse;
}

export async function verifyWebBatch(payload: {
  provider: "gemini" | "openai" | "both";
  items: Array<{ id: string; user_question: string; a1: string; a2: string; user_challenge?: string | null }>;
  max_items?: number;
}): Promise<{ results: Array<{ id: string; provider: string; model: string; update_answer_correctness: boolean | null; raw: any }> }> {
  const res = await fetch(`${API_BASE}/api/verify_web_batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return (await res.json()) as any;
}

export function downloadUrl(path: string): string {
  if (path.startsWith("http")) return path;
  return `${API_BASE}${path}`;
}
