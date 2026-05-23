from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


Severity = Literal["informational", "low", "medium", "high", "critical"]


# ─── Audit ──────────────────────────────────────────────────────────────────

class SourceAuditRequest(BaseModel):
    source: str = Field(..., description="Solidity source code")
    filename: str = "Contract.sol"
    solc_version: Optional[str] = None
    use_slither: bool = True
    use_mythril: bool = False
    use_mempool: bool = True
    use_honeypot: bool = True
    use_ai: bool = False
    persist: bool = False  # save to history


class AddressAuditRequest(BaseModel):
    address: str
    chain: Literal["eth", "bsc", "polygon", "arbitrum"] = "eth"
    use_slither: bool = True
    use_mythril: bool = False
    use_mempool: bool = True
    use_honeypot: bool = True
    use_ai: bool = False
    persist: bool = False


class Finding(BaseModel):
    id: str
    title: str
    severity: Severity
    description: str
    detector: str  # custom | slither | mythril | mempool | honeypot | ai
    file: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    code_snippet: Optional[str] = None
    recommendation: Optional[str] = None
    references: List[str] = []
    ai_explanation: Optional[str] = None


class AuditMeta(BaseModel):
    filename: str
    sloc: int
    contracts: List[str] = []
    duration_ms: int
    detectors_run: List[str]
    timestamp: str


class AuditReport(BaseModel):
    meta: AuditMeta
    findings: List[Finding]
    summary: Dict[str, int]


class ReportExportRequest(BaseModel):
    report: AuditReport
    format: Literal["markdown", "json", "pdf"] = "markdown"


# ─── Honeypot ───────────────────────────────────────────────────────────────

class HoneypotIndicator(BaseModel):
    name: str
    severity: Severity
    description: str
    evidence: Optional[str] = None
    line: Optional[int] = None


class HoneypotReport(BaseModel):
    risk_score: int  # 0-100
    is_likely_honeypot: bool
    indicators: List[HoneypotIndicator]
    summary: str


# ─── Call Graph ─────────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str
    label: str
    contract: str
    visibility: Literal["public", "external", "internal", "private"] = "internal"
    is_constructor: bool = False
    has_modifier: bool = False
    line: Optional[int] = None


class GraphEdge(BaseModel):
    source: str
    target: str
    type: Literal["call", "inheritance", "modifier"] = "call"


class CallGraph(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    contracts: List[str]
    inheritance: Dict[str, List[str]] = {}


class GraphRequest(BaseModel):
    source: str


# ─── Diff Audit ─────────────────────────────────────────────────────────────

class DiffAuditRequest(BaseModel):
    source_old: str
    source_new: str
    filename: str = "Contract.sol"
    use_slither: bool = True


class DiffFindingDelta(BaseModel):
    added: List[Finding]
    removed: List[Finding]
    unchanged_count: int


class DiffResult(BaseModel):
    unified_diff: str
    lines_added: int
    lines_removed: int
    old_report: AuditReport
    new_report: AuditReport
    delta: DiffFindingDelta


# ─── History ────────────────────────────────────────────────────────────────

class HistoryEntry(BaseModel):
    id: int
    filename: str
    contracts: List[str]
    summary: Dict[str, int]
    sloc: int
    detectors_run: List[str]
    timestamp: str


class HistoryListResponse(BaseModel):
    entries: List[HistoryEntry]
    total: int


class HistoryDetailResponse(BaseModel):
    id: int
    timestamp: str
    source: str
    report: AuditReport
