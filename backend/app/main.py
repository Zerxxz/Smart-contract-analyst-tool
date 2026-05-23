from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import audit, report


app = FastAPI(
    title="Smart Contract Auditor API",
    description="Static analysis & audit tooling for Solidity contracts",
    version="0.1.0",
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


@app.get("/")
async def root():
    return {
        "name": "Smart Contract Auditor",
        "version": "0.1.0",
        "docs": "/docs",
    }
