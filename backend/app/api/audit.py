import re
import time
from datetime import datetime, timezone
from collections import Counter
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    SourceAuditRequest, AddressAuditRequest, AuditReport, AuditMeta, Finding,
)
from app.analyzers import custom_detectors, slither_runner, ai_explainer
from app.api.onchain import fetch_source


router = APIRouter(prefix="/audit", tags=["audit"])


def _summarize(findings: List[Finding]) -> dict:
    counter = Counter(f.severity for f in findings)
    return {sev: counter.get(sev, 0) for sev in
            ("critical", "high", "medium", "low", "informational")}


def _extract_contract_names(source: str) -> List[str]:
    return re.findall(r"\bcontract\s+(\w+)", source)


def _audit_pipeline(source: str, filename: str, solc_version: Optional[str],
                    use_slither: bool, use_ai: bool) -> AuditReport:
    if not source.strip():
        raise HTTPException(400, "Source code is empty")
    if len(source) > 500_000:
        raise HTTPException(413, "Source too large (>500KB)")

    t0 = time.time()
    findings: List[Finding] = []
    detectors_run = ["custom"]

    findings.extend(custom_detectors.run_all(source))

    if use_slither and slither_runner.is_available():
        detectors_run.append("slither")
        findings.extend(slither_runner.run(source, filename, solc_version))

    if use_ai:
        detectors_run.append("ai")
        for f in findings:
            if f.severity in ("critical", "high", "medium"):
                f.ai_explanation = ai_explainer.explain(f, source)

    # Sort by severity
    sev_order = {"critical": 0, "high": 1, "medium": 2,
                 "low": 3, "informational": 4}
    findings.sort(key=lambda f: sev_order.get(f.severity, 5))

    duration_ms = int((time.time() - t0) * 1000)
    meta = AuditMeta(
        filename=filename,
        sloc=len(source.splitlines()),
        contracts=_extract_contract_names(source),
        duration_ms=duration_ms,
        detectors_run=detectors_run,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    return AuditReport(meta=meta, findings=findings,
                       summary=_summarize(findings))


@router.post("/source", response_model=AuditReport)
async def audit_source(req: SourceAuditRequest):
    return _audit_pipeline(req.source, req.filename, req.solc_version,
                           req.use_slither, req.use_ai)


@router.post("/address", response_model=AuditReport)
async def audit_address(req: AddressAuditRequest):
    if not re.match(r"^0x[a-fA-F0-9]{40}$", req.address):
        raise HTTPException(400, "Invalid address format")
    try:
        source, name = await fetch_source(req.address, req.chain)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return _audit_pipeline(source, f"{name}.sol", None,
                           req.use_slither, req.use_ai)


@router.get("/health")
async def health():
    return {
        "ok": True,
        "slither_available": slither_runner.is_available(),
        "detectors": custom_detectors.detector_names(),
    }
