"""
Honeypot / rug-pull detector for ERC-20-like contracts.

Produces a HoneypotReport with a 0-100 risk score and a list of weighted
indicators. Aggregation is greedy: any single critical indicator is enough
to flag a contract as likely-honeypot.
"""
import re
from typing import List, Tuple
from app.models.schemas import HoneypotReport, HoneypotIndicator


# Each rule -> (name, severity, weight, description, regex_pattern,
#               recommendation_for_user)
# Weights sum-clamped to 100. Any rule with `critical` severity is enough
# alone to trigger likely-honeypot.

def _line_of(source: str, idx: int) -> int:
    return source[:idx].count("\n") + 1


def _evidence(source: str, m: re.Match) -> str:
    line_no = _line_of(source, m.start())
    line_text = source.splitlines()[line_no - 1].strip()
    return f"L{line_no}: {line_text[:120]}"


# ─── Individual indicator checks ────────────────────────────────────────────

def _check_high_tax(source: str) -> List[HoneypotIndicator]:
    out = []
    # Look for fee/tax variables set to high values
    for m in re.finditer(
            r"(?:uint\d*\s+)?(\w*[Tt]ax\w*|\w*[Ff]ee\w*)\s*=\s*(\d+)", source):
        try:
            val = int(m.group(2))
        except ValueError:
            continue
        # Heuristic: tax expressed in percent (>20) or basis points (>2000)
        if val > 20 and val <= 100:
            pct = val
        elif val > 2000 and val <= 10000:
            pct = val / 100
        else:
            continue
        sev = "critical" if pct > 50 else "high"
        out.append(HoneypotIndicator(
            name="High buy/sell tax",
            severity=sev,
            description=f"Tax/fee variable `{m.group(1)}` is set to {pct}%, "
                        "which leaves users with little or none of their "
                        "tokens after a transfer.",
            evidence=_evidence(source, m),
            line=_line_of(source, m.start()),
        ))
    return out


def _check_modifiable_tax(source: str) -> List[HoneypotIndicator]:
    """Owner can change tax to arbitrary value."""
    out = []
    pattern = re.compile(
        r"function\s+(\w*[Ss]et\w*[Tt]ax\w*|\w*[Ss]et\w*[Ff]ee\w*)\s*\(",
    )
    for m in pattern.finditer(source):
        # Find the function body to inspect for upper bounds
        body_start = source.find("{", m.end())
        body_end = source.find("}", body_start)
        body = source[body_start:body_end] if body_start > 0 else ""
        bounded = bool(re.search(
            r"require\s*\([^)]*<\s*=?\s*\d+", body))
        sev = "high" if bounded else "critical"
        desc = (f"Function `{m.group(1)}` allows the owner to change the "
                "tax/fee" + (" but enforces an upper bound."
                             if bounded else
                             ", with no upper bound — owner can set tax "
                             "to 100%."))
        out.append(HoneypotIndicator(
            name="Owner-modifiable tax",
            severity=sev,
            description=desc,
            evidence=_evidence(source, m),
            line=_line_of(source, m.start()),
        ))
    return out


def _check_blacklist(source: str) -> List[HoneypotIndicator]:
    out = []
    if re.search(r"\b(blacklist|isBlacklisted|_blacklist|blocked)\b",
                 source, re.IGNORECASE):
        m = re.search(r"\b(blacklist|isBlacklisted|_blacklist|blocked)\b",
                      source, re.IGNORECASE)
        out.append(HoneypotIndicator(
            name="Blacklist mechanism present",
            severity="high",
            description="Contract contains a blacklist mapping or function. "
                        "Owner can permanently freeze any address from "
                        "transferring, including legitimate holders.",
            evidence=_evidence(source, m) if m else None,
            line=_line_of(source, m.start()) if m else None,
        ))
    return out


def _check_pausable_transfer(source: str) -> List[HoneypotIndicator]:
    out = []
    has_pause = bool(re.search(
        r"function\s+(pause|setTrading|enableTrading|tradingEnabled)\b",
        source))
    transfer_gated = bool(re.search(
        r"function\s+_?transfer\b[^{]*\{[^}]*"
        r"(require|if)\s*\([^)]*(paused|tradingEnabled|tradingOpen)",
        source, re.DOTALL))
    if has_pause and transfer_gated:
        m = re.search(r"function\s+(pause|setTrading|enableTrading)\b",
                      source)
        out.append(HoneypotIndicator(
            name="Owner-controlled trading pause",
            severity="high",
            description="Transfers are gated by an owner-controlled flag. "
                        "After buyers acquire tokens, the owner can "
                        "permanently disable selling.",
            evidence=_evidence(source, m) if m else None,
            line=_line_of(source, m.start()) if m else None,
        ))
    return out


def _check_hidden_mint(source: str) -> List[HoneypotIndicator]:
    out = []
    pattern = re.compile(
        r"function\s+(\w*[Mm]int\w*)\s*\([^)]*\)[^{]*"
        r"(?!.*(?:onlyOwner|MINTER_ROLE|onlyRole))[^{]*\{",
        re.DOTALL,
    )
    # Also flag any owner-mint with no supply cap
    for m in re.finditer(r"function\s+(mint|_mint)\s*\(", source):
        body_start = source.find("{", m.end())
        body_end = source.find("}", body_start)
        body = source[body_start:body_end] if body_start > 0 else ""
        # Check if there's a max supply check
        capped = bool(re.search(
            r"(MAX_SUPPLY|maxSupply|cap|MAX_TOTAL_SUPPLY)", body))
        if capped:
            continue
        # Owner-only mint without cap is still a rug vector
        out.append(HoneypotIndicator(
            name="Uncapped mint function",
            severity="high",
            description="Mint function lacks an enforced supply cap. Owner "
                        "(or whoever holds the role) can dilute holders by "
                        "minting unlimited tokens.",
            evidence=_evidence(source, m),
            line=_line_of(source, m.start()),
        ))
    return out


def _check_transfer_override(source: str) -> List[HoneypotIndicator]:
    out = []
    # Custom _transfer with conditional revert based on sender being owner
    pattern = re.compile(
        r"function\s+_?transfer\b[^{]*\{(?P<body>(?:[^{}]|\{[^{}]*\})*)\}",
        re.DOTALL,
    )
    for m in pattern.finditer(source):
        body = m.group("body")
        # Buyer-only logic: revert if sender != owner / pair
        if re.search(
                r"(require|if)\s*\([^)]*(msg\.sender|from)\s*"
                r"(==|!=)\s*(owner|_owner)", body):
            out.append(HoneypotIndicator(
                name="Sender-restricted transfer logic",
                severity="critical",
                description="Custom `_transfer` reverts based on `msg.sender` "
                            "or `from` being or not being the owner. This is "
                            "the canonical 'only owner can sell' honeypot.",
                evidence=_evidence(source, m),
                line=_line_of(source, m.start()),
            ))
    return out


def _check_fake_renounce(source: str) -> List[HoneypotIndicator]:
    out = []
    if re.search(r"function\s+renounceOwnership", source):
        # Look for hidden owner / authorizedAddress / dev wallet still active
        if re.search(r"(_dev|_authorized|_secondaryOwner|isAdmin)\s*=",
                     source):
            m = re.search(r"renounceOwnership", source)
            out.append(HoneypotIndicator(
                name="Suspicious dual-ownership pattern",
                severity="high",
                description="Contract exposes `renounceOwnership` but also "
                            "maintains a secondary admin/dev address. After "
                            "'renouncing', the owner may still control "
                            "privileged functions.",
                evidence=_evidence(source, m) if m else None,
                line=_line_of(source, m.start()) if m else None,
            ))
    return out


def _check_balance_override(source: str) -> List[HoneypotIndicator]:
    """Owner can directly write to user balances."""
    out = []
    pattern = re.compile(
        r"function\s+(\w+)\s*\([^)]*\)[^{]*onlyOwner[^{]*\{"
        r"(?P<body>(?:[^{}]|\{[^{}]*\})*)\}",
        re.DOTALL,
    )
    for m in pattern.finditer(source):
        body = m.group("body")
        if re.search(r"_?balances?\s*\[[^\]]+\]\s*=", body):
            out.append(HoneypotIndicator(
                name="Owner can directly modify user balances",
                severity="critical",
                description=f"Owner-only function `{m.group(1)}` writes "
                            "directly to `balances[..]`. Owner can wipe or "
                            "inflate any user's balance.",
                evidence=_evidence(source, m),
                line=_line_of(source, m.start()),
            ))
    return out


def _check_max_tx_owner_controlled(source: str) -> List[HoneypotIndicator]:
    out = []
    if re.search(r"function\s+set(MaxTx|maxWallet|MaxAmount)", source):
        m = re.search(r"function\s+set(MaxTx|maxWallet|MaxAmount)", source)
        out.append(HoneypotIndicator(
            name="Owner-controlled max-tx / max-wallet",
            severity="medium",
            description="Owner can set transfer or wallet limits at any time, "
                        "which can be used to prevent users from selling "
                        "meaningful amounts.",
            evidence=_evidence(source, m) if m else None,
            line=_line_of(source, m.start()) if m else None,
        ))
    return out


# ─── Aggregator ─────────────────────────────────────────────────────────────

ALL_CHECKS = [
    _check_high_tax,
    _check_modifiable_tax,
    _check_blacklist,
    _check_pausable_transfer,
    _check_hidden_mint,
    _check_transfer_override,
    _check_fake_renounce,
    _check_balance_override,
    _check_max_tx_owner_controlled,
]


_SEVERITY_WEIGHT = {
    "critical": 50,
    "high": 25,
    "medium": 10,
    "low": 5,
    "informational": 0,
}


def analyze(source: str) -> HoneypotReport:
    indicators: List[HoneypotIndicator] = []
    for check in ALL_CHECKS:
        try:
            indicators.extend(check(source))
        except Exception as e:  # noqa: BLE001
            print(f"[honeypot] {check.__name__} failed: {e}")

    # Score
    score = 0
    for ind in indicators:
        score += _SEVERITY_WEIGHT.get(ind.severity, 0)
    score = min(100, score)

    # If no token-like surface at all, lower the floor
    is_token = bool(
        re.search(r"function\s+(transfer|balanceOf|totalSupply)", source))
    if not is_token:
        score = max(0, score - 10)

    likely = (
        score >= 60
        or any(i.severity == "critical" for i in indicators)
    )

    if not indicators:
        summary = ("No honeypot indicators detected. This does NOT prove the "
                   "contract is safe — only that common rug-patterns are "
                   "absent.")
    elif likely:
        summary = (f"⚠️  {len(indicators)} honeypot indicator(s) detected, "
                   f"risk score {score}/100. Treat this contract as "
                   "high-risk until proven safe via runtime testing.")
    else:
        summary = (f"{len(indicators)} indicator(s) found, risk score "
                   f"{score}/100. Some patterns are concerning but not "
                   "individually conclusive.")

    return HoneypotReport(
        risk_score=score,
        is_likely_honeypot=likely,
        indicators=indicators,
        summary=summary,
    )
