"""
AI-assisted explanation per finding. Uses Anthropic or OpenAI depending on
config. Best-effort: silently skips if no key configured.
"""
from typing import Optional
from app.core.config import settings
from app.models.schemas import Finding


SYSTEM_PROMPT = (
    "You are a senior smart-contract security auditor. "
    "Given a Solidity finding, produce a concise (max 120 words) "
    "explanation covering: (1) why this is dangerous, (2) a real-world "
    "example or attack scenario, (3) the recommended fix in code. "
    "Use plain language and markdown. Do NOT repeat the finding title."
)


def _build_user_prompt(finding: Finding, source: Optional[str]) -> str:
    parts = [
        f"## Finding: {finding.title}",
        f"Severity: {finding.severity}",
        f"Description: {finding.description}",
    ]
    if finding.code_snippet:
        parts.append(f"Code:\n```solidity\n{finding.code_snippet}\n```")
    return "\n\n".join(parts)


def explain(finding: Finding, source: Optional[str] = None) -> Optional[str]:
    provider = settings.ai_provider.lower()
    if provider == "anthropic" and settings.anthropic_api_key:
        return _explain_anthropic(finding, source)
    if provider == "openai" and settings.openai_api_key:
        return _explain_openai(finding, source)
    if provider == "minimax" and settings.minimax_api_key:
        return _explain_minimax(finding, source)
    return None


def _explain_anthropic(finding: Finding, source: Optional[str]) -> Optional[str]:
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=settings.anthropic_api_key)
        msg = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user",
                       "content": _build_user_prompt(finding, source)}],
        )
        return msg.content[0].text if msg.content else None
    except Exception as e:  # noqa: BLE001
        print(f"[ai_explainer] anthropic failed: {e}")
        return None


def _explain_openai(finding: Finding, source: Optional[str]) -> Optional[str]:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",
                 "content": _build_user_prompt(finding, source)},
            ],
            max_tokens=400,
        )
        return resp.choices[0].message.content
    except Exception as e:  # noqa: BLE001
        print(f"[ai_explainer] openai failed: {e}")
        return None


def _explain_minimax(finding: Finding, source: Optional[str]) -> Optional[str]:
    try:
        import httpx
        payload = {
            "model": settings.minimax_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",
                 "content": _build_user_prompt(finding, source)},
            ],
            "max_tokens": 400,
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {settings.minimax_api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=60) as client:
            r = client.post(
                settings.minimax_base_url,
                json=payload,
                headers=headers,
            )
        r.raise_for_status()
        data = r.json()
        base = data.get("base_resp") or {}
        if base.get("status_code") and base.get("status_code") != 0:
            print(f"[ai_explainer] minimax api error: {base}")
            return None
        choices = data.get("choices") or []
        if not choices:
            return None
        content = (choices[0].get("message") or {}).get("content") or ""
        if isinstance(content, list):
            content = "".join(
                blk.get("text", "") for blk in content
                if isinstance(blk, dict)
            )
        return content or None
    except Exception as e:  # noqa: BLE001
        print(f"[ai_explainer] minimax failed: {e}")
        return None
