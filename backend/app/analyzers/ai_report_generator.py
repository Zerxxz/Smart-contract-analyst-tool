"""
AI-curated audit report generator.

Takes raw detector findings + optional honeypot scoring, then either:
1. Calls Claude/OpenAI to synthesize a structured AIAuditReport, or
2. Falls back to a deterministic templated report (still well-formatted)

The fallback ensures the UX is consistent even without an API key.
"""
import json
import re
from typing import List, Optional

from app.core.config import settings
from app.models.schemas import (
    AIAuditReport, AuditReport, Finding, HoneypotReport, KeyFinding,
)


SYSTEM_PROMPT = """You are a senior smart-contract security auditor.
You produce executive-quality audit reports for Solidity contracts.

Given a contract's source code and findings from automated analyzers, output a
STRICT JSON object with this exact shape:

{
  "overall_score": <int 0-100, 100 = pristine>,
  "risk_level": "safe" | "low_risk" | "moderate_risk" | "high_risk" | "critical_risk",
  "one_line_verdict": "<single sentence>",
  "executive_summary": "<markdown, 2-3 paragraphs>",
  "key_findings": [
    {
      "title": "<concise>",
      "severity": "critical" | "high" | "medium" | "low" | "informational",
      "location": "<function name + line>",
      "explanation": "<plain-language, why this is wrong>",
      "impact": "<what an attacker can do>",
      "fix": "<what to change, imperative>",
      "code_before": "<exact affected snippet, max 12 lines>",
      "code_after": "<patched version, max 14 lines>",
      "references": ["<url>", ...]
    }
  ],
  "code_quality_notes": "<markdown bullet list on style/gas/patterns>",
  "recommendations": ["<imperative action>", ...]
}

Strict rules:
- Output ONLY the JSON object. No prose before or after. No markdown fences.
- Be specific. Use the actual function/variable names from the contract.
- Group duplicate detector findings into a single key_finding.
- Sort key_findings by severity (critical -> informational).
- Provide compilable code_after snippets. Preserve original indentation.
- If contract is essentially safe, say so confidently. Score >=85 means safe.
- Limit total response to 6000 tokens.
"""


# --- Public API -------------------------------------------------------------

def generate(source: str, raw_report: AuditReport,
             honeypot: Optional[HoneypotReport] = None) -> AIAuditReport:
    """Try AI; fall back to deterministic template on any failure."""
    provider = settings.ai_provider.lower()
    if provider == "anthropic" and settings.anthropic_api_key:
        ai = _call_anthropic(source, raw_report, honeypot)
        if ai is not None:
            return ai
    elif provider == "openai" and settings.openai_api_key:
        ai = _call_openai(source, raw_report, honeypot)
        if ai is not None:
            return ai
    elif provider == "minimax" and settings.minimax_api_key:
        ai = _call_minimax(source, raw_report, honeypot)
        if ai is not None:
            return ai
    return _template_fallback(source, raw_report, honeypot)


# --- AI providers -----------------------------------------------------------

def _build_user_prompt(source: str, report: AuditReport,
                       honeypot: Optional[HoneypotReport]) -> str:
    parts = [
        "## Contract source",
        "```solidity",
        source[:30_000],
        "```",
        "",
        "## Detector findings",
        "",
    ]
    if not report.findings:
        parts.append("_No detector findings._")
    for f in report.findings:
        parts.append(f"### [{f.severity}] {f.title} ({f.detector})")
        if f.line_start:
            parts.append(f"Line: {f.line_start}")
        parts.append(f"Description: {f.description}")
        if f.recommendation:
            parts.append(f"Recommendation: {f.recommendation}")
        if f.code_snippet:
            parts.append("```")
            parts.append(f.code_snippet[:600])
            parts.append("```")
        parts.append("")
    if honeypot and honeypot.indicators:
        parts.append("## Honeypot indicators")
        parts.append(f"Risk score: {honeypot.risk_score}/100")
        for ind in honeypot.indicators:
            parts.append(f"- [{ind.severity}] {ind.name}: {ind.description}")
    parts.append("")
    parts.append("Now produce the structured JSON audit report.")
    return "\n".join(parts)


def _call_anthropic(source, report, honeypot) -> Optional[AIAuditReport]:
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=settings.anthropic_api_key)
        msg = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=6000,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": _build_user_prompt(source, report, honeypot),
            }],
        )
        text = "".join(
            block.text for block in msg.content
            if getattr(block, "text", None)
        )
        return _parse_ai_json(text, report, honeypot, ai=True)
    except Exception as e:  # noqa: BLE001
        print(f"[ai_report] anthropic failed: {e}")
        return None


def _call_openai(source, report, honeypot) -> Optional[AIAuditReport]:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            max_tokens=6000,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",
                 "content": _build_user_prompt(source, report, honeypot)},
            ],
        )
        text = resp.choices[0].message.content or ""
        return _parse_ai_json(text, report, honeypot, ai=True)
    except Exception as e:  # noqa: BLE001
        print(f"[ai_report] openai failed: {e}")
        return None


def _call_minimax(source, report, honeypot) -> Optional[AIAuditReport]:
    """MiniMax chat completion (OpenAI-compatible)."""
    try:
        import httpx
        payload = {
            "model": settings.minimax_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",
                 "content": _build_user_prompt(source, report, honeypot)},
            ],
            "max_tokens": 6000,
            "temperature": 0.1,
        }
        headers = {
            "Authorization": f"Bearer {settings.minimax_api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=120) as client:
            r = client.post(
                settings.minimax_base_url,
                json=payload,
                headers=headers,
            )
        r.raise_for_status()
        data = r.json()
        # Surface API-level errors (MiniMax sometimes returns 200 with
        # a non-zero status_code in base_resp)
        base = data.get("base_resp") or {}
        if base.get("status_code") and base.get("status_code") != 0:
            print(f"[ai_report] minimax api error: {base}")
            return None
        choices = data.get("choices") or []
        if not choices:
            return None
        msg = choices[0].get("message") or {}
        text = msg.get("content") or ""
        if isinstance(text, list):  # some servers return content blocks
            text = "".join(
                blk.get("text", "") for blk in text
                if isinstance(blk, dict)
            )
        return _parse_ai_json(text, report, honeypot, ai=True)
    except Exception as e:  # noqa: BLE001
        print(f"[ai_report] minimax failed: {e}")
        return None


def _parse_ai_json(text: str, raw_report: AuditReport,
                   honeypot: Optional[HoneypotReport],
                   ai: bool) -> Optional[AIAuditReport]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    end = -1
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end == -1:
        return None
    try:
        data = json.loads(text[start:end])
    except json.JSONDecodeError:
        return None

    try:
        return AIAuditReport(
            overall_score=int(data.get("overall_score", 50)),
            risk_level=data.get("risk_level", "moderate_risk"),
            one_line_verdict=str(data.get("one_line_verdict", "")),
            is_ai_generated=ai,
            executive_summary=str(data.get("executive_summary", "")),
            key_findings=[
                KeyFinding(**kf) for kf in data.get("key_findings", [])
            ],
            code_quality_notes=str(data.get("code_quality_notes", "")),
            recommendations=list(data.get("recommendations", []) or []),
            raw_report=raw_report,
            honeypot=honeypot,
        )
    except Exception as e:  # noqa: BLE001
        print(f"[ai_report] invalid AI JSON shape: {e}")
        return None


# --- Deterministic fallback -------------------------------------------------

_SEVERITY_WEIGHT = {
    "critical": 35, "high": 18, "medium": 8, "low": 3, "informational": 1,
}


def _compute_score(report: AuditReport) -> int:
    deduction = 0
    for f in report.findings:
        deduction += _SEVERITY_WEIGHT.get(f.severity, 0)
    return max(0, 100 - deduction)


def _risk_from_score(score: int):
    if score >= 85:
        return "safe"
    if score >= 70:
        return "low_risk"
    if score >= 50:
        return "moderate_risk"
    if score >= 25:
        return "high_risk"
    return "critical_risk"


def _verdict(report: AuditReport, score: int) -> str:
    s = report.summary
    crit = s.get("critical", 0)
    high = s.get("high", 0)
    if crit > 0:
        return (f"Contract has {crit} critical-severity issue"
                f"{'s' if crit > 1 else ''} that must be fixed before "
                "deployment.")
    if high > 2:
        return (f"Multiple high-severity concerns ({high}) - significant "
                "remediation needed.")
    if high > 0:
        return (f"{high} high-severity issue"
                f"{'s' if high > 1 else ''} should be addressed before "
                "production.")
    if score >= 85:
        return ("Contract appears to follow best practices; only minor "
                "informational notes were found.")
    return ("Contract has moderate concerns worth reviewing before "
            "deployment.")


def _executive_summary(report: AuditReport, score: int,
                       honeypot: Optional[HoneypotReport]) -> str:
    s = report.summary
    contracts = ", ".join(report.meta.contracts) or "unknown"
    total = sum(s.values())
    parts = [
        f"This automated audit analyzed **{contracts}** "
        f"({report.meta.sloc} lines) using "
        f"{len(report.meta.detectors_run)} detector "
        f"engine{'s' if len(report.meta.detectors_run) != 1 else ''}: "
        f"`{', '.join(report.meta.detectors_run)}`.",
    ]
    if total == 0:
        parts.append(
            "**No issues were flagged.** The contract passes all enabled "
            "static checks. This does not guarantee the absence of bugs - "
            "manual review and runtime testing remain essential."
        )
    else:
        breakdown = []
        for sev in ("critical", "high", "medium", "low", "informational"):
            n = s.get(sev, 0)
            if n:
                breakdown.append(f"{n} {sev}")
        parts.append(
            f"**{total} issue{'s' if total != 1 else ''} identified**: "
            f"{', '.join(breakdown)}. Overall security score: "
            f"**{score}/100**."
        )
    if honeypot and honeypot.is_likely_honeypot:
        parts.append(
            f"**Honeypot indicators detected** "
            f"(risk score {honeypot.risk_score}/100). Treat as unsafe until "
            "manually verified on a fork."
        )
    return "\n\n".join(parts)


def _location_str(f: Finding) -> str:
    if f.line_start and f.line_end and f.line_end != f.line_start:
        return f"line {f.line_start}-{f.line_end}"
    if f.line_start:
        return f"line {f.line_start}"
    return f.file or "global"


def _to_key_finding(f: Finding) -> KeyFinding:
    snippet = None
    if f.code_snippet:
        snippet = "\n".join(
            re.sub(r"^\s*\d+\s*\|\s?", "", line)
            for line in f.code_snippet.splitlines()
        )
    return KeyFinding(
        title=f.title,
        severity=f.severity,
        location=_location_str(f),
        explanation=f.description,
        impact=_impact_for(f),
        fix=f.recommendation or "Review the highlighted code.",
        code_before=snippet,
        code_after=None,
        references=f.references or [],
    )


def _impact_for(f: Finding) -> str:
    title = f.title.lower()
    if "reentrancy" in title:
        return ("An attacker contract can recursively re-enter the "
                "function and drain funds before state updates settle.")
    if "tx.origin" in title:
        return ("If a user is tricked into calling a malicious contract, "
                "their authority is impersonated.")
    if "selfdestruct" in title:
        return ("Contract can be permanently destroyed; funds and logic "
                "may become irrecoverable.")
    if "honeypot" in title:
        return "Buyers may be unable to sell or transfer tokens."
    if "slippage" in title:
        return ("Users can be sandwich-attacked; trade output can be "
                "extracted via flashloans.")
    if "oracle" in title:
        return "Spot price can be flash-loan manipulated within a single tx."
    if "access control" in title or "lack" in title:
        return ("Anyone can invoke the privileged function and change "
                "critical state.")
    if "zero" in title:
        return ("Misconfiguration can permanently brick the contract or "
                "send funds to a black-hole address.")
    return f"Severity: {f.severity}. Review and remediate before deployment."


def _code_quality_notes(report: AuditReport) -> str:
    info = [f for f in report.findings
            if f.severity in ("informational", "low")]
    if not info:
        return ("- No notable code-quality issues flagged by automated "
                "detectors.\n- Recommend manual review of gas patterns and "
                "naming conventions.")
    bullets = []
    seen = set()
    for f in info:
        key = f.title
        if key in seen:
            continue
        seen.add(key)
        bullets.append(f"- **{f.title}** - {f.description.split('.')[0]}.")
    return "\n".join(bullets)


def _recommendations(report: AuditReport,
                     honeypot: Optional[HoneypotReport]) -> List[str]:
    recs: List[str] = []
    seen = set()
    sev_order = {"critical": 0, "high": 1, "medium": 2,
                 "low": 3, "informational": 4}
    for f in sorted(
            report.findings,
            key=lambda x: sev_order.get(x.severity, 5)):
        if not f.recommendation:
            continue
        key = f.recommendation[:80]
        if key in seen:
            continue
        seen.add(key)
        recs.append(f.recommendation)
    if honeypot and honeypot.is_likely_honeypot:
        recs.insert(0,
            "Do NOT interact with this contract on mainnet. Verify "
            "transfer behavior on a fork before any deposit.")
    if not recs:
        recs.append(
            "Manually review the contract against the SWC registry checklist "
            "(https://swcregistry.io) and add invariant tests via Foundry."
        )
    return recs[:12]


def _template_fallback(source: str, report: AuditReport,
                       honeypot: Optional[HoneypotReport]) -> AIAuditReport:
    score = _compute_score(report)
    risk = _risk_from_score(score)
    if honeypot and honeypot.is_likely_honeypot:
        score = min(score, 20)
        risk = "critical_risk"

    sev_order = {"critical": 0, "high": 1, "medium": 2,
                 "low": 3, "informational": 4}
    sorted_findings = sorted(
        report.findings, key=lambda f: sev_order.get(f.severity, 5))
    seen = set()
    deduped = []
    for f in sorted_findings:
        if f.title in seen:
            continue
        seen.add(f.title)
        deduped.append(f)
    key_findings = [_to_key_finding(f) for f in deduped[:12]]

    return AIAuditReport(
        overall_score=score,
        risk_level=risk,
        one_line_verdict=_verdict(report, score),
        is_ai_generated=False,
        executive_summary=_executive_summary(report, score, honeypot),
        key_findings=key_findings,
        code_quality_notes=_code_quality_notes(report),
        recommendations=_recommendations(report, honeypot),
        raw_report=report,
        honeypot=honeypot,
    )
