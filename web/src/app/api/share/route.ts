import { NextResponse } from "next/server";
import { MongoClient } from "mongodb";
import { loadEnvFallback } from "../_lib/dotenv";

const DB_NAME = process.env.MONGODB_DB ?? "ai_safety";
const COLLECTION_NAME = process.env.MONGODB_COLLECTION ?? "SwayBench";

let _client: MongoClient | null = null;
async function client() {
  if (_client) return _client;
  loadEnvFallback();
  const uri = process.env.MONGODB_URI;
  if (!uri) throw new Error("Missing MONGODB_URI");
  _client = new MongoClient(uri);
  await _client.connect();
  return _client;
}

const EMAIL_RE = /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i;
const OPENAI_KEY_RE = /\bsk-[A-Za-z0-9]{20,}\b/;
const GOOGLE_KEY_RE = /\bAIza[0-9A-Za-z\-_]{20,}\b/;

function looksUnanonymized(s: string) {
  const t = s ?? "";
  if (EMAIL_RE.test(t)) return true;
  if (OPENAI_KEY_RE.test(t) || GOOGLE_KEY_RE.test(t)) return true;
  return false;
}

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as { items: any[]; meta?: Record<string, any> };
    const items = (body.items ?? []).slice(0, 500);
    if (!items.length) return NextResponse.json({ error: "No items provided." }, { status: 400 });

    // Basic guardrail: reject if it looks like raw secrets/PII were uploaded.
    for (const it of items.slice(0, 50)) {
      const blob = `${it.user_question ?? ""}\n${it.user_challenge ?? ""}\n${it.a1_sanitized ?? ""}\n${it.a2_sanitized ?? ""}`;
      if (looksUnanonymized(blob)) {
        return NextResponse.json(
          { error: "Upload appears to contain unanonymized content. Please anonymize before sharing." },
          { status: 400 }
        );
      }
    }

    const batch_id = crypto.randomUUID();
    const now = new Date();
    const docs = items.map((it) => ({
      batch_id,
      created_at: now,
      id: String(it.id ?? ""),
      evidence_flag: !!it.evidence_flag,
      signals: it.signals ?? {},
      ui: it.ui ?? {},
      user_question: String(it.user_question ?? ""),
      user_challenge: String(it.user_challenge ?? ""),
      a1_anonymized: String(it.a1_sanitized ?? ""),
      a2_anonymized: String(it.a2_sanitized ?? ""),
      meta: body.meta ?? {}
    }));

    const c = await client();
    const col = c.db(DB_NAME).collection(COLLECTION_NAME);
    const r = await col.insertMany(docs, { ordered: false });

    return NextResponse.json({
      ok: true,
      batch_id,
      inserted: r.insertedCount,
      db: DB_NAME,
      collection: COLLECTION_NAME
    });
  } catch (e: any) {
    return NextResponse.json({ error: e?.message ?? String(e) }, { status: 400 });
  }
}
