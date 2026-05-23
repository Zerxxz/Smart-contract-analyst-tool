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
