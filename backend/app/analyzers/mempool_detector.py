"""
Mempool exposure analyzer.

Detects MEV-vulnerable patterns: front-running, sandwich attacks, missing
slippage protection, single-block oracle reads, commit-without-reveal.

Heuristic / pattern-based — complements but does not replace simulation.
"""
import re
import uuid
from typing import List
from app.models.schemas import Finding


def _line_of(source: str, idx: int) -> int:
    return source[:idx].count("\n") + 1


def _snippet(source: str, line: int, ctx: int = 2) -> str:
    lines = source.splitlines()
    s, e = max(0, line - 1 - ctx), min(len(lines), line + ctx)
    return "\n".join(f"{i+1:4d} | {lines[i]}" for i in range(s, e))


def _mk(title: str, severity: str, desc: str, source: str, line: int,
        recommendation: str = "", refs=None) -> Finding:
    return Finding(
        id=str(uuid.uuid4())[:8],
        title=title,
        severity=severity,
        description=desc,
        detector="mempool",
        line_start=line,
        line_end=line,
        code_snippet=_snippet(source, line),
        recommendation=recommendation,
        references=refs or [],
    )


def _iter_functions(source: str):
    """Yield (head, body, body_offset) for each function definition."""
    pattern = re.compile(
        r"function\s+(?P<name>\w+)\s*\([^)]*\)[^{]*\{"
        r"(?P<body>(?:[^{}]|\{[^{}]*\})*)\}",
        re.DOTALL,
    )
    for m in pattern.finditer(source):
        head_end = m.start("body")
        head = source[m.start():head_end]
        yield m.group("name"), head, m.group("body"), m.start("body")


# ─── Detectors ──────────────────────────────────────────────────────────────

def detect_missing_slippage(source: str) -> List[Finding]:
    """Swap-like functions without minOut/amountOutMin parameter."""
    findings = []
    SWAP_KEYWORDS = ("swap", "exchange", "trade", "buy", "sell")
    for name, head, body, body_off in _iter_functions(source):
        lname = name.lower()
        if not any(k in lname for k in SWAP_KEYWORDS):
            continue
        if "view" in head or "pure" in head:
            continue
        # Look at parameter list in head
        params_match = re.search(r"\(([^)]*)\)", head)
        params = params_match.group(1) if params_match else ""
        has_min_out = re.search(
            r"(minOut|amountOutMin|minAmountOut|deadline|minReceive)",
            params + body, re.IGNORECASE)
        if not has_min_out:
            line = _line_of(source, body_off - len(head))
            findings.append(_mk(
                title=f"Possible missing slippage protection in `{name}`",
                severity="high",
                desc=f"Swap-like function `{name}` does not appear to accept "
                     "a `minAmountOut`/`deadline` parameter. This makes the "
                     "function vulnerable to sandwich attacks where an "
                     "attacker front-runs and back-runs the user's tx.",
                source=source, line=line,
                recommendation="Add `minAmountOut` and `deadline` parameters "
                               "and revert if the actual output is below the "
                               "user-specified minimum.",
                refs=["https://swcregistry.io/docs/SWC-114"],
            ))
    return findings


def detect_spot_price_oracle(source: str) -> List[Finding]:
    """getReserves() / .reserve usage without TWAP - sandwich-prone."""
    findings = []
    pattern = re.compile(
        r"\.(getReserves|getAmountsOut|price0CumulativeLast|"
        r"price1CumulativeLast|reserve0|reserve1)\s*(?:\(|\b)",
        re.IGNORECASE,
    )
    seen_lines = set()
    for m in pattern.finditer(source):
        line = _line_of(source, m.start())
        if line in seen_lines:
            continue
        seen_lines.add(line)
        # Skip if there's a TWAP/observe call nearby (Uniswap V3)
        window = source[max(0, m.start() - 500):m.start() + 500]
        if re.search(r"\b(observe|twap|TWAP|cumulativePrice)\b", window):
            continue
        findings.append(_mk(
            title="Spot-price oracle usage (sandwich-vulnerable)",
            severity="high",
            desc="Reading on-chain spot price (e.g. Uniswap V2 reserves or "
                 "`getAmountsOut`) directly is vulnerable to manipulation "
                 "via flash loans and sandwich attacks, since the pool can "
                 "be temporarily skewed within a single transaction.",
            source=source, line=line,
            recommendation="Use a time-weighted average price (TWAP) such as "
                           "Uniswap V3 `observe()` or a Chainlink oracle "
                           "with a heartbeat check.",
            refs=[
                "https://blog.openzeppelin.com/secure-smart-contract-guidelines-the-dangers-of-price-oracles/",
                "https://docs.uniswap.org/concepts/protocol/oracle"
            ],
        ))
    return findings


def detect_public_state_setters_no_commit(source: str) -> List[Finding]:
    """
    Publicly callable functions that set sensitive parameters without a
    commit-reveal scheme — front-runnable.
    """
    findings = []
    SENSITIVE = ("price", "rate", "fee", "tax", "feeRate", "exchangeRate",
                 "rewardRate")
    pattern = re.compile(
        r"function\s+(?P<name>\w+)\s*\(([^)]*)\)\s+(public|external)"
        r"(?![^{]*(?:onlyOwner|onlyRole|nonReentrant|view|pure))[^{]*\{"
        r"(?P<body>(?:[^{}]|\{[^{}]*\})*)\}",
        re.DOTALL,
    )
    for m in pattern.finditer(source):
        body = m.group("body")
        name = m.group("name")
        head = source[m.start():m.start("body")]
        if "view" in head or "pure" in head:
            continue
        # Body writes to a sensitive state variable
        for kw in SENSITIVE:
            if re.search(rf"\b{kw}\w*\s*=", body, re.IGNORECASE):
                line = _line_of(source, m.start())
                findings.append(_mk(
                    title=f"Front-runnable state mutation in `{name}`",
                    severity="medium",
                    desc=f"Function `{name}` updates a sensitive parameter "
                         f"(`{kw}`-like) and is publicly callable without an "
                         "access modifier or commit-reveal scheme. An "
                         "attacker observing the mempool can front-run the "
                         "transaction.",
                    source=source, line=line,
                    recommendation="Restrict the function with proper access "
                                   "control, or use a commit-reveal scheme "
                                   "with a delay before the value takes "
                                   "effect.",
                    refs=["https://swcregistry.io/docs/SWC-114"],
                ))
                break
    return findings


def detect_approve_race(source: str) -> List[Finding]:
    """ERC-20 approve race condition (SWC-114 derivative)."""
    findings = []
    # Look for `approve(address, uint)` implementation that does
    # plain `allowance[..] = value` without enforcing zero-first.
    pattern = re.compile(
        r"function\s+approve\s*\([^)]*\)[^{]*\{(?P<body>(?:[^{}]|\{[^{}]*\})*)\}",
        re.DOTALL,
    )
    for m in pattern.finditer(source):
        body = m.group("body")
        if "increaseAllowance" in body or "decreaseAllowance" in body:
            continue
        if re.search(r"allowance\s*\[[^\]]+\]\s*\[[^\]]+\]\s*==\s*0", body):
            continue  # likely already protected
        line = _line_of(source, m.start())
        findings.append(_mk(
            title="ERC-20 `approve` race condition",
            severity="medium",
            desc="A standard `approve(spender, value)` allows an attacker "
                 "with a pending allowance to front-run a re-approval and "
                 "spend both the old and new allowance.",
            source=source, line=line,
            recommendation="Provide and recommend `increaseAllowance` / "
                           "`decreaseAllowance`, or require the previous "
                           "allowance to be zero before setting a new one.",
            refs=["https://swcregistry.io/docs/SWC-114"],
        ))
    return findings


def detect_first_depositor_donation(source: str) -> List[Finding]:
    """ERC-4626/share-vault first-depositor inflation attack pattern."""
    findings = []
    has_share_logic = bool(re.search(
        r"(totalShares|totalSupply|_mint\s*\([^)]+,\s*shares|"
        r"shares\s*=\s*amount\s*\*\s*totalSupply\s*/)",
        source))
    if not has_share_logic:
        return []
    has_donation_protection = bool(re.search(
        r"(initialDeposit|virtual_shares|VIRTUAL_SHARES|_decimalsOffset|"
        r"deadShares)",
        source, re.IGNORECASE))
    if has_donation_protection:
        return []
    # Heuristic: only flag if vault-like (deposit + shares)
    if re.search(r"function\s+deposit", source) and \
       re.search(r"shares\s*=\s*amount", source, re.IGNORECASE):
        m = re.search(r"function\s+deposit", source)
        line = _line_of(source, m.start()) if m else 1
        findings.append(_mk(
            title="Possible ERC-4626 first-depositor inflation attack",
            severity="high",
            desc="Share-based vault appears to mint shares proportional to "
                 "amount/totalSupply without virtual share donation "
                 "protection. The first depositor can be sandwiched: "
                 "attacker deposits 1 wei, donates a large amount directly "
                 "to the vault, then the victim's shares round to zero.",
            source=source, line=line,
            recommendation="Implement OpenZeppelin's ERC4626 `_decimalsOffset` "
                           "or seed the vault with virtual shares "
                           "(`deadShares`) at deployment.",
            refs=[
                "https://blog.openzeppelin.com/a-novel-defense-against-erc4626-inflation-attacks",
            ],
        ))
    return findings


def detect_block_number_randomness(source: str) -> List[Finding]:
    """blockhash / block.number / block.difficulty used for randomness."""
    findings = []
    pattern = re.compile(
        r"\b(blockhash|block\.difficulty|block\.prevrandao|block\.number)\b",
    )
    for m in pattern.finditer(source):
        # Heuristic: only flag if used in arithmetic / hashing context
        window = source[max(0, m.start() - 80):m.start() + 80]
        if not re.search(r"(keccak256|sha256|%|abi\.encodePacked|uint\()",
                         window):
            continue
        line = _line_of(source, m.start())
        findings.append(_mk(
            title="Block-based pseudo-randomness",
            severity="high",
            desc=f"`{m.group(0)}` is used in what appears to be a "
                 "randomness-generating context. Validators / searchers can "
                 "predict or manipulate these values within the mempool.",
            source=source, line=line,
            recommendation="Use Chainlink VRF, drand, or a commit-reveal "
                           "scheme for any value that affects financial "
                           "outcomes.",
            refs=[
                "https://swcregistry.io/docs/SWC-120",
                "https://docs.chain.link/vrf/v2/introduction",
            ],
        ))
    return findings


ALL_DETECTORS = [
    detect_missing_slippage,
    detect_spot_price_oracle,
    detect_public_state_setters_no_commit,
    detect_approve_race,
    detect_first_depositor_donation,
    detect_block_number_randomness,
]


def run_all(source: str) -> List[Finding]:
    findings: List[Finding] = []
    for d in ALL_DETECTORS:
        try:
            findings.extend(d(source))
        except Exception as e:  # noqa: BLE001
            print(f"[mempool_detector] {d.__name__} failed: {e}")
    return findings


def detector_names() -> List[str]:
    return [d.__name__.replace("detect_", "") for d in ALL_DETECTORS]
