import type { AuditReport } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function handle<T>(r: Response): Promise<T> {
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`API ${r.status}: ${text}`);
  }
  return r.json() as Promise<T>;
}

export async function auditSource(opts: {
  source: string;
  filename?: string;
  use_slither?: boolean;
  use_ai?: boolean;
}): Promise<AuditReport> {
  const r = await fetch(`${API_URL}/audit/source`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source: opts.source,
      filename: opts.filename ?? "Contract.sol",
      use_slither: opts.use_slither ?? true,
      use_ai: opts.use_ai ?? false,
    }),
  });
  return handle<AuditReport>(r);
}

export async function auditAddress(opts: {
  address: string;
  chain: string;
  use_slither?: boolean;
  use_ai?: boolean;
}): Promise<AuditReport> {
  const r = await fetch(`${API_URL}/audit/address`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      address: opts.address,
      chain: opts.chain,
      use_slither: opts.use_slither ?? true,
      use_ai: opts.use_ai ?? false,
    }),
  });
  return handle<AuditReport>(r);
}

export async function exportReport(
  report: AuditReport,
  format: "markdown" | "json"
): Promise<string> {
  const r = await fetch(`${API_URL}/report/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report, format }),
  });
  if (!r.ok) throw new Error(`Export failed: ${r.status}`);
  if (format === "json") return JSON.stringify(await r.json(), null, 2);
  return r.text();
}

export async function getHealth() {
  const r = await fetch(`${API_URL}/audit/health`);
  return handle<{
    ok: boolean;
    slither_available: boolean;
    detectors: string[];
  }>(r);
}
