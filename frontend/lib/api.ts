import type {
  AuditReport, AuditOpts,
  HoneypotReport, CallGraph, DiffResult,
  HistoryListResponse, HistoryDetailResponse,
  AIAuditReport,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function handle<T>(r: Response): Promise<T> {
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`API ${r.status}: ${text}`);
  }
  return r.json() as Promise<T>;
}

function defaults(opts: AuditOpts) {
  return {
    source: opts.source,
    filename: opts.filename ?? "Contract.sol",
    use_slither: opts.use_slither ?? true,
    use_mythril: opts.use_mythril ?? false,
    use_mempool: opts.use_mempool ?? true,
    use_honeypot: opts.use_honeypot ?? true,
    use_ai: opts.use_ai ?? false,
    persist: opts.persist ?? false,
  };
}

// ─── Audit ──────────────────────────────────────────────────────────────
export async function auditSource(opts: AuditOpts): Promise<AuditReport> {
  const r = await fetch(`${API_URL}/audit/source`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(defaults(opts)),
  });
  return handle<AuditReport>(r);
}

export async function auditAddress(opts: {
  address: string;
  chain: string;
  use_slither?: boolean;
  use_mythril?: boolean;
  use_mempool?: boolean;
  use_honeypot?: boolean;
  use_ai?: boolean;
  persist?: boolean;
}): Promise<AuditReport> {
  const r = await fetch(`${API_URL}/audit/address`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      address: opts.address,
      chain: opts.chain,
      use_slither: opts.use_slither ?? true,
      use_mythril: opts.use_mythril ?? false,
      use_mempool: opts.use_mempool ?? true,
      use_honeypot: opts.use_honeypot ?? true,
      use_ai: opts.use_ai ?? false,
      persist: opts.persist ?? false,
    }),
  });
  return handle<AuditReport>(r);
}

// --- AI Audit (one-shot) ---------------------------------------------------
export async function aiAudit(opts: {
  source: string;
  filename?: string;
  persist?: boolean;
}): Promise<AIAuditReport> {
  const r = await fetch(`${API_URL}/audit/ai-report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source: opts.source,
      filename: opts.filename ?? "Contract.sol",
      persist: opts.persist ?? false,
    }),
  });
  return handle<AIAuditReport>(r);
}

// --- Honeypot --------------------------------------------------------------
export async function honeypotSource(source: string): Promise<HoneypotReport> {
  const r = await fetch(`${API_URL}/honeypot/source`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source }),
  });
  return handle<HoneypotReport>(r);
}

// ─── Call Graph ─────────────────────────────────────────────────────────
export async function buildGraph(source: string): Promise<CallGraph> {
  const r = await fetch(`${API_URL}/graph/source`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source }),
  });
  return handle<CallGraph>(r);
}

// ─── Diff ───────────────────────────────────────────────────────────────
export async function diffAudit(opts: {
  source_old: string;
  source_new: string;
  filename?: string;
  use_slither?: boolean;
}): Promise<DiffResult> {
  const r = await fetch(`${API_URL}/diff/audit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source_old: opts.source_old,
      source_new: opts.source_new,
      filename: opts.filename ?? "Contract.sol",
      use_slither: opts.use_slither ?? true,
    }),
  });
  return handle<DiffResult>(r);
}

// ─── History ────────────────────────────────────────────────────────────
export async function listHistory(limit = 50, offset = 0): Promise<HistoryListResponse> {
  const r = await fetch(`${API_URL}/history?limit=${limit}&offset=${offset}`);
  return handle<HistoryListResponse>(r);
}

export async function getHistoryItem(id: number): Promise<HistoryDetailResponse> {
  const r = await fetch(`${API_URL}/history/${id}`);
  return handle<HistoryDetailResponse>(r);
}

export async function deleteHistoryItem(id: number): Promise<void> {
  const r = await fetch(`${API_URL}/history/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error(`Delete failed: ${r.status}`);
}

// ─── Reports ────────────────────────────────────────────────────────────
export async function exportReport(
  report: AuditReport,
  format: "markdown" | "json" | "pdf"
): Promise<Blob | string> {
  const r = await fetch(`${API_URL}/report/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report, format }),
  });
  if (!r.ok) throw new Error(`Export failed: ${r.status}`);
  if (format === "pdf") return r.blob();
  if (format === "json") return JSON.stringify(await r.json(), null, 2);
  return r.text();
}

export async function getHealth() {
  const r = await fetch(`${API_URL}/audit/health`);
  return handle<{
    ok: boolean;
    slither_available: boolean;
    mythril_available: boolean;
    ai_provider: string;
    ai_configured: boolean;
    detectors: { custom: string[]; mempool: string[] };
  }>(r);
}
