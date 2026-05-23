import re
import time
import uuid
from datetime import datetime, timezone
from collections import Counter
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    SourceAuditRequest, AddressAuditRequest, AuditReport, AuditMeta, Finding,
)
from app.analyzers import (
    custom_detectors, slither_runner, ai_explainer,
    mempool_detector, honeypot_detector, mythril_runner,
)
from app.api.onchain import fetch_source
from app.db import database


router = APIRouter(prefix="/audit", tags=["audit"])


def _summarize(findings: List[Finding]) -> dict:
    counter = Counter(f.severity for f in findings)
    return {sev: counter.get(sev, 0) for sev in
            ("critical", "high", "medium", "low", "informational")}


def _extract_contract_names(source: str) -> List[str]:
    return re.findall(r"\bcontract\s+(\w+)", source)


def _honeypot_to_findings(source: str) -> List[Finding]:
    """Flatten HoneypotReport indicators into Finding objects so they appear
    in the unified findings list. The structured HoneypotReport remains
    available via the /honeypot endpoint."""
    report = honeypot_detector.analyze(source)
    findings: List[Finding] = []
    for ind in report.indicators:
        snippet = None
        if ind.line:
            lines = source.splitlines()
            s, e = max(0, ind.line - 3), min(len(lines), ind.line + 2)
            snippet = "\n".join(
                f"{i+1:4d} | {lines[i]}" for i in range(s, e))
        findings.append(Finding(
            id=str(uuid.uuid4())[:8],
            title=f"Honeypot: {ind.name}",
            severity=ind.severity,
            description=ind.description,
            detector="honeypot",
            line_start=ind.line,
            line_end=ind.line,
            code_snippet=snippet,
            recommendation="Verify the contract's runtime behavior on a "
                           "fork. Treat as high-risk until proven safe.",
            references=[
                "https://github.com/ColumboMaster/awesome-honeypot-tokens"
            ],
        ))
    return findings


def _audit_pipeline(source: str, filename: str, solc_version: Optional[str],
                    use_slither: bool, use_mythril: bool,
                    use_mempool: bool, use_honeypot: bool,
                    use_ai: bool, persist: bool) -> AuditReport:
    if not source.strip():
        raise HTTPException(400, "Source code is empty")
    if len(source) > 500_000:
        raise HTTPException(413, "Source too large (>500KB)")

    t0 = time.time()
    findings: List[Finding] = []
    detectors_run = ["custom"]

    findings.extend(custom_detectors.run_all(source))

    if use_mempool:
        detectors_run.append("mempool")
        findings.extend(mempool_detector.run_all(source))

    if use_honeypot:
        detectors_run.append("honeypot")
        findings.extend(_honeypot_to_findings(source))

    if use_slither and slither_runner.is_available():
        detectors_run.append("slither")
        findings.extend(slither_runner.run(source, filename, solc_version))

    if use_mythril and mythril_runner.is_available():
        detectors_run.append("mythril")
        findings.extend(mythril_runner.run(source, filename, solc_version))

    if use_ai:
        detectors_run.append("ai")
        for f in findings:
            if f.severity in ("critical", "high", "medium"):
                f.ai_explanation = ai_explainer.explain(f, source)

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
    report = AuditReport(
        meta=meta, findings=findings, summary=_summarize(findings))

    if persist:
        try:
            database.save_audit(report, source)
        except Exception as e:  # noqa: BLE001
            print(f"[audit] persist failed: {e}")
    return report


@router.post("/source", response_model=AuditReport)
async def audit_source(req: SourceAuditRequest):
    return _audit_pipeline(
        source=req.source,
        filename=req.filename,
        solc_version=req.solc_version,
        use_slither=req.use_slither,
        use_mythril=req.use_mythril,
        use_mempool=req.use_mempool,
        use_honeypot=req.use_honeypot,
        use_ai=req.use_ai,
        persist=req.persist,
    )


@router.post("/address", response_model=AuditReport)
async def audit_address(req: AddressAuditRequest):
    if not re.match(r"^0x[a-fA-F0-9]{40}$", req.address):
        raise HTTPException(400, "Invalid address format")
    try:
        source, name = await fetch_source(req.address, req.chain)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return _audit_pipeline(
        source=source,
        filename=f"{name}.sol",
        solc_version=None,
        use_slither=req.use_slither,
        use_mythril=req.use_mythril,
        use_mempool=req.use_mempool,
        use_honeypot=req.use_honeypot,
        use_ai=req.use_ai,
        persist=req.persist,
    )


@router.get("/health")
async def health():
    return {
        "ok": True,
        "slither_available": slither_runner.is_available(),
        "mythril_available": mythril_runner.is_available(),
        "detectors": {
            "custom": custom_detectors.detector_names(),
            "mempool": mempool_detector.detector_names(),
        },
    }
