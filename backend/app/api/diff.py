"""Diff audit endpoints — compare two contract versions."""
from fastapi import APIRouter, HTTPException
from app.models.schemas import DiffAuditRequest, DiffResult
from app.analyzers import diff_analyzer
from app.api.audit import _audit_pipeline


router = APIRouter(prefix="/diff", tags=["diff"])


@router.post("/audit", response_model=DiffResult)
async def diff_audit(req: DiffAuditRequest):
    if not req.source_old.strip() or not req.source_new.strip():
        raise HTTPException(400, "Both source_old and source_new are required")

    old_report = _audit_pipeline(
        source=req.source_old, filename=f"old/{req.filename}",
        solc_version=None, use_slither=req.use_slither,
        use_mythril=False, use_mempool=True, use_honeypot=True,
        use_ai=False, persist=False,
    )
    new_report = _audit_pipeline(
        source=req.source_new, filename=f"new/{req.filename}",
        solc_version=None, use_slither=req.use_slither,
        use_mythril=False, use_mempool=True, use_honeypot=True,
        use_ai=False, persist=False,
    )
    return diff_analyzer.build_diff_result(
        req.source_old, req.source_new, req.filename,
        old_report, new_report,
    )
