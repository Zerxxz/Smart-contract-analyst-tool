"""Markdown / JSON / PDF report export."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse, Response
from app.models.schemas import ReportExportRequest, AuditReport
from app.analyzers import pdf_renderer


router = APIRouter(prefix="/report", tags=["report"])


SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
    "informational": "⚪",
}


def render_markdown(report: AuditReport) -> str:
    m = report.meta
    s = report.summary
    lines = [
        f"# Smart Contract Audit Report",
        "",
        f"**File:** `{m.filename}`  ",
        f"**Contracts:** {', '.join(m.contracts) or '_none detected_'}  ",
        f"**SLOC:** {m.sloc}  ",
        f"**Detectors:** {', '.join(m.detectors_run)}  ",
        f"**Duration:** {m.duration_ms} ms  ",
        f"**Timestamp:** {m.timestamp}  ",
        "",
        "## Severity Summary",
        "",
        "| Severity | Count |",
        "|---|---|",
        f"| 🔴 Critical | {s.get('critical', 0)} |",
        f"| 🟠 High | {s.get('high', 0)} |",
        f"| 🟡 Medium | {s.get('medium', 0)} |",
        f"| 🔵 Low | {s.get('low', 0)} |",
        f"| ⚪ Informational | {s.get('informational', 0)} |",
        "",
        "## Findings",
        "",
    ]
    if not report.findings:
        lines.append("_No findings — clean run._")
    for i, f in enumerate(report.findings, 1):
        emoji = SEVERITY_EMOJI.get(f.severity, "")
        lines.append(f"### {i}. {emoji} {f.title}")
        lines.append("")
        lines.append(f"- **Severity:** `{f.severity}`")
        lines.append(f"- **Detector:** `{f.detector}`")
        if f.line_start:
            loc = f"line {f.line_start}"
            if f.line_end and f.line_end != f.line_start:
                loc = f"lines {f.line_start}-{f.line_end}"
            lines.append(f"- **Location:** {loc}")
        lines.append("")
        lines.append(f"**Description:** {f.description}")
        lines.append("")
        if f.code_snippet:
            lines.append("```solidity")
            lines.append(f.code_snippet)
            lines.append("```")
            lines.append("")
        if f.recommendation:
            lines.append(f"**Recommendation:** {f.recommendation}")
            lines.append("")
        if f.ai_explanation:
            lines.append("**AI Analysis:**")
            lines.append("")
            lines.append(f.ai_explanation)
            lines.append("")
        if f.references:
            lines.append("**References:**")
            for r in f.references:
                lines.append(f"- {r}")
            lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


@router.post("/export")
async def export_report(req: ReportExportRequest):
    if req.format == "json":
        return JSONResponse(req.report.model_dump())
    if req.format == "pdf":
        try:
            pdf_bytes = pdf_renderer.render(req.report)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(500, f"PDF render failed: {e}")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition":
                    'attachment; filename="audit-report.pdf"',
            },
        )
    return PlainTextResponse(render_markdown(req.report),
                             media_type="text/markdown")
