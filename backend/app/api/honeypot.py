"""Honeypot risk-scoring endpoints."""
import re
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    SourceAuditRequest, AddressAuditRequest, HoneypotReport,
)
from app.analyzers import honeypot_detector
from app.api.onchain import fetch_source


router = APIRouter(prefix="/honeypot", tags=["honeypot"])


@router.post("/source", response_model=HoneypotReport)
async def analyze_source(req: SourceAuditRequest):
    if not req.source.strip():
        raise HTTPException(400, "Source code is empty")
    return honeypot_detector.analyze(req.source)


@router.post("/address", response_model=HoneypotReport)
async def analyze_address(req: AddressAuditRequest):
    if not re.match(r"^0x[a-fA-F0-9]{40}$", req.address):
        raise HTTPException(400, "Invalid address format")
    try:
        source, _ = await fetch_source(req.address, req.chain)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return honeypot_detector.analyze(source)
