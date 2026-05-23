from typing import List, Optional, Literal
from pydantic import BaseModel, Field


Severity = Literal["informational", "low", "medium", "high", "critical"]


class SourceAuditRequest(BaseModel):
    source: str = Field(..., description="Solidity source code")
    filename: str = "Contract.sol"
    solc_version: Optional[str] = None
    use_slither: bool = True
    use_ai: bool = False


class AddressAuditRequest(BaseModel):
    address: str
    chain: Literal["eth", "bsc", "polygon", "arbitrum"] = "eth"
    use_slither: bool = True
    use_ai: bool = False


class Finding(BaseModel):
    id: str
    title: str
    severity: Severity
    description: str
    detector: str  # "custom" | "slither" | "ai"
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
    summary: dict  # {"critical": n, "high": n, ...}


class ReportExportRequest(BaseModel):
    report: AuditReport
    format: Literal["markdown", "json"] = "markdown"
