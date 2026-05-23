"""Call graph extraction endpoints."""
import re
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    CallGraph, GraphRequest, AddressAuditRequest,
)
from app.analyzers import call_graph
from app.api.onchain import fetch_source


router = APIRouter(prefix="/graph", tags=["graph"])


@router.post("/source", response_model=CallGraph)
async def graph_source(req: GraphRequest):
    if not req.source.strip():
        raise HTTPException(400, "Source code is empty")
    return call_graph.build(req.source)


@router.post("/address", response_model=CallGraph)
async def graph_address(req: AddressAuditRequest):
    if not re.match(r"^0x[a-fA-F0-9]{40}$", req.address):
        raise HTTPException(400, "Invalid address format")
    try:
        source, _ = await fetch_source(req.address, req.chain)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return call_graph.build(source)
