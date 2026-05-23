export type Severity =
  | "critical"
  | "high"
  | "medium"
  | "low"
  | "informational";

export interface Finding {
  id: string;
  title: string;
  severity: Severity;
  description: string;
  detector: string;
  file?: string | null;
  line_start?: number | null;
  line_end?: number | null;
  code_snippet?: string | null;
  recommendation?: string | null;
  references: string[];
  ai_explanation?: string | null;
}

export interface AuditMeta {
  filename: string;
  sloc: number;
  contracts: string[];
  duration_ms: number;
  detectors_run: string[];
  timestamp: string;
}

export interface AuditReport {
  meta: AuditMeta;
  findings: Finding[];
  summary: Record<Severity, number>;
}
