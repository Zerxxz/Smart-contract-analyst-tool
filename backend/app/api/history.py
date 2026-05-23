"""Audit history CRUD endpoints."""
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import HistoryListResponse, HistoryDetailResponse
from app.db import database


router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=HistoryListResponse)
async def list_history(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    entries, total = database.list_audits(limit=limit, offset=offset)
    return HistoryListResponse(entries=entries, total=total)


@router.get("/{audit_id}", response_model=HistoryDetailResponse)
async def get_history(audit_id: int):
    entry = database.get_audit(audit_id)
    if not entry:
        raise HTTPException(404, "Audit not found")
    return entry


@router.delete("/{audit_id}")
async def delete_history(audit_id: int):
    if not database.delete_audit(audit_id):
        raise HTTPException(404, "Audit not found")
    return {"deleted": audit_id}
