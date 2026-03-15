import fs from "node:fs";
import path from "node:path";

function parseDotenv(text: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq <= 0) continue;
    const key = line.slice(0, eq).trim();
    let val = line.slice(eq + 1).trim();
    if ((val.startsWith("\"") && val.endsWith("\"")) || (val.startsWith("'") && val.endsWith("'"))) {
      val = val.slice(1, -1);
    }
    if (key) out[key] = val;
  }
  return out;
}

export function loadEnvFallback(): { loaded: boolean; pathTried: string[] } {
  const tried: string[] = [];

  // Next.js normally loads `web/.env.local` and friends. This is only a fallback for local dev
  // when users put secrets in the repo-root `.env`.
  const candidates = [
    path.join(process.cwd(), ".env"),
    path.join(process.cwd(), "..", ".env"),
    path.join(process.cwd(), "..", "..", ".env")
  ];

  for (const p of candidates) {
    tried.push(p);
    try {
      if (!fs.existsSync(p)) continue;
      const txt = fs.readFileSync(p, "utf-8");
      const env = parseDotenv(txt);
      let changed = false;
      for (const [k, v] of Object.entries(env)) {
        if (process.env[k] === undefined) {
          process.env[k] = v;
          changed = true;
        }
      }
      return { loaded: changed, pathTried: tried };
    } catch {
      continue;
    }
  }

  return { loaded: false, pathTried: tried };
}

