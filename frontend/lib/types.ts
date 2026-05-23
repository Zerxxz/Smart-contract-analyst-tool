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

export interface HoneypotIndicator {
  name: string;
  severity: Severity;
  description: string;
  evidence?: string | null;
  line?: number | null;
}

export interface HoneypotReport {
  risk_score: number;
  is_likely_honeypot: boolean;
  indicators: HoneypotIndicator[];
  summary: string;
}

export interface GraphNode {
  id: string;
  label: string;
  contract: string;
  visibility: "public" | "external" | "internal" | "private";
  is_constructor: boolean;
  has_modifier: boolean;
  line?: number | null;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: "call" | "inheritance" | "modifier";
}

export interface CallGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  contracts: string[];
  inheritance: Record<string, string[]>;
}

export interface DiffFindingDelta {
  added: Finding[];
  removed: Finding[];
  unchanged_count: number;
}

export interface DiffResult {
  unified_diff: string;
  lines_added: number;
  lines_removed: number;
  old_report: AuditReport;
  new_report: AuditReport;
  delta: DiffFindingDelta;
}

export interface HistoryEntry {
  id: number;
  filename: string;
  contracts: string[];
  summary: Record<Severity, number>;
  sloc: number;
  detectors_run: string[];
  timestamp: string;
}

export interface HistoryListResponse {
  entries: HistoryEntry[];
  total: number;
}

export interface HistoryDetailResponse {
  id: number;
  timestamp: string;
  source: string;
  report: AuditReport;
}

export interface AuditOpts {
  source: string;
  filename?: string;
  use_slither?: boolean;
  use_mythril?: boolean;
  use_mempool?: boolean;
  use_honeypot?: boolean;
  use_ai?: boolean;
  persist?: boolean;
}
