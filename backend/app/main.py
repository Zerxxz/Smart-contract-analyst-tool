from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import audit, report, honeypot, graph, diff, history


app = FastAPI(
    title="Smart Contract Auditor API",
    description="Static analysis & deep audit tooling for Solidity contracts",
    version="0.2.0",
)

origins = [settings.frontend_origin]
if settings.frontend_origin == "*":
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audit.router)
app.include_router(report.router)
app.include_router(honeypot.router)
app.include_router(graph.router)
app.include_router(diff.router)
app.include_router(history.router)


@app.get("/")
async def root():
    return {
        "name": "Smart Contract Auditor",
        "version": "0.2.0",
        "docs": "/docs",
        "endpoints": [
            "/audit/source", "/audit/address", "/audit/health",
            "/honeypot/source", "/honeypot/address",
            "/graph/source", "/graph/address",
            "/diff/audit",
            "/history", "/history/{id}",
            "/report/export",
        ],
    }
