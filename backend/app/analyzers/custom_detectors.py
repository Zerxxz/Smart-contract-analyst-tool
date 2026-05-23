"""
Custom heuristic detectors for Solidity source code.
Pure-Python regex/AST-lite checks that run without external tools.
These complement Slither and provide a useful baseline.
"""
import re
import uuid
from typing import List
from app.models.schemas import Finding


def _snippet(source: str, line: int, ctx: int = 2) -> str:
    lines = source.splitlines()
    start = max(0, line - 1 - ctx)
    end = min(len(lines), line + ctx)
    return "\n".join(f"{i+1:4d} | {lines[i]}" for i in range(start, end))


def _line_of(source: str, match_start: int) -> int:
    return source[:match_start].count("\n") + 1


def _mk(title: str, severity: str, desc: str, source: str, line: int,
        recommendation: str = "", refs=None) -> Finding:
    return Finding(
        id=str(uuid.uuid4())[:8],
        title=title,
        severity=severity,
        description=desc,
        detector="custom",
        line_start=line,
        line_end=line,
        code_snippet=_snippet(source, line),
        recommendation=recommendation,
        references=refs or [],
    )


def detect_tx_origin(source: str) -> List[Finding]:
    findings = []
    for m in re.finditer(r"\btx\.origin\b", source):
        findings.append(_mk(
            title="Use of tx.origin for authorization",
            severity="high",
            desc="`tx.origin` should not be used for authorization. It is "
                 "vulnerable to phishing-style attacks via intermediate "
                 "contracts.",
            source=source, line=_line_of(source, m.start()),
            recommendation="Use `msg.sender` instead of `tx.origin`.",
            refs=["https://swcregistry.io/docs/SWC-115"],
        ))
    return findings


def detect_unchecked_low_level_call(source: str) -> List[Finding]:
    findings = []
    pattern = re.compile(
        r"(?P<full>\.(call|delegatecall|send)\s*(\{[^}]*\})?\s*\([^)]*\))"
        r"(?P<after>[^;]{0,40})", re.MULTILINE)
    for m in pattern.finditer(source):
        full = m.group("full")
        after = m.group("after") or ""
        # Already destructured or assigned -> probably checked
        if re.search(r"\(\s*bool\s+\w+", source[max(0, m.start() - 60):m.start()]):
            continue
        if "require" in after or "if" in after or "=" in after:
            continue
        findings.append(_mk(
            title="Unchecked low-level call",
            severity="medium",
            desc="Return value of a low-level call is not checked. Failed "
                 "calls will silently continue execution.",
            source=source, line=_line_of(source, m.start()),
            recommendation="Check the boolean return value: "
                           "`(bool ok, ) = addr.call{...}(...); require(ok);`",
            refs=["https://swcregistry.io/docs/SWC-104"],
        ))
    return findings


def detect_reentrancy_pattern(source: str) -> List[Finding]:
    """
    Naive pattern: external call followed by state write within same function.
    Real reentrancy detection needs Slither — this catches the obvious case.
    """
    findings = []
    fn_pattern = re.compile(
        r"function\s+\w+[^{]*\{(?P<body>(?:[^{}]|\{[^{}]*\})*)\}",
        re.DOTALL)
    # Skip nonReentrant guarded functions
    for fn in fn_pattern.finditer(source):
        head_start = max(0, fn.start() - 0)
        fn_head = source[fn.start():fn.start("body")]
        if "nonReentrant" in fn_head:
            continue
        body = fn.group("body")
        body_offset = fn.start("body")
        # Detect external call: .call(...), .delegatecall(...), .send(...),
        # .transfer(...) or low-level call with value: .call{value: ...}(...)
        call_match = re.search(
            r"\.(call|delegatecall|send|transfer)\s*(\{[^}]*\})?\s*\(", body)
        if not call_match:
            continue
        after_call = body[call_match.end():]
        # State write: identifier (optionally with [..] or .x access) followed
        # by = / += / -= (but not ==)
        write = re.search(
            r"\b([a-zA-Z_]\w*)(?:\[[^\]]*\]|\.\w+)*\s*([+\-*/]?=)(?!=)",
            after_call)
        if write:
            line = _line_of(source, body_offset + call_match.start())
            var_name = write.group(1)
            findings.append(_mk(
                title="Possible reentrancy (state write after external call)",
                severity="critical",
                desc=f"External call is followed by a state write to "
                     f"`{var_name}` within the same function. This pattern "
                     f"is vulnerable to reentrancy attacks (e.g. The DAO). "
                     f"State changes must happen BEFORE external calls.",
                source=source, line=line,
                recommendation="Use Checks-Effects-Interactions pattern: "
                               "update state first, then make external "
                               "calls. Alternatively use OpenZeppelin's "
                               "`ReentrancyGuard` (`nonReentrant` modifier).",
                refs=["https://swcregistry.io/docs/SWC-107"],
            ))
    return findings


def detect_pragma_floating(source: str) -> List[Finding]:
    findings = []
    for m in re.finditer(r"pragma\s+solidity\s+(\^|>=?|<=?)([^;]+);", source):
        op = m.group(1)
        if op in ("^", ">=", ">"):
            findings.append(_mk(
                title="Floating pragma",
                severity="informational",
                desc=f"Contract uses a floating pragma `{m.group(0)}`. "
                     "Production contracts should be locked to a specific "
                     "compiler version.",
                source=source, line=_line_of(source, m.start()),
                recommendation="Lock the pragma to a specific version, e.g. "
                               "`pragma solidity 0.8.24;`",
                refs=["https://swcregistry.io/docs/SWC-103"],
            ))
    return findings


def detect_block_timestamp(source: str) -> List[Finding]:
    findings = []
    for m in re.finditer(r"\bblock\.timestamp\b|\bnow\b", source):
        findings.append(_mk(
            title="Reliance on block.timestamp",
            severity="low",
            desc="`block.timestamp` (or `now`) can be manipulated by miners "
                 "by up to ~15 seconds. Avoid using it for critical logic "
                 "such as randomness or precise timing.",
            source=source, line=_line_of(source, m.start()),
            recommendation="Use block numbers or oracles for time-sensitive "
                           "or randomness-sensitive logic.",
            refs=["https://swcregistry.io/docs/SWC-116"],
        ))
    return findings


def detect_selfdestruct(source: str) -> List[Finding]:
    findings = []
    for m in re.finditer(r"\b(selfdestruct|suicide)\s*\(", source):
        findings.append(_mk(
            title="Use of selfdestruct",
            severity="high",
            desc="Contract uses `selfdestruct`, which is deprecated and can "
                 "lead to permanent fund loss or unexpected behavior after "
                 "EIP-6780.",
            source=source, line=_line_of(source, m.start()),
            recommendation="Avoid selfdestruct. Use access-controlled "
                           "pause/upgrade patterns instead.",
            refs=["https://eips.ethereum.org/EIPS/eip-6780"],
        ))
    return findings


def detect_missing_zero_check(source: str) -> List[Finding]:
    """Find address parameters in setters/transferOwnership without zero-check."""
    findings = []
    pattern = re.compile(
        r"function\s+(?P<name>set\w+|transferOwnership)\s*\("
        r"(?P<params>[^)]*address[^)]*)\)[^{]*\{(?P<body>[^}]*)\}",
        re.DOTALL)
    for m in pattern.finditer(source):
        body = m.group("body")
        if "address(0)" not in body and "!= address(0)" not in body:
            findings.append(_mk(
                title=f"Missing zero-address check in `{m.group('name')}`",
                severity="medium",
                desc="Function accepts an address parameter without "
                     "validating it is non-zero. Setting to address(0) may "
                     "brick the contract or send funds to an unrecoverable "
                     "address.",
                source=source, line=_line_of(source, m.start()),
                recommendation="Add `require(newAddr != address(0), \"zero "
                               "addr\");`",
                refs=["https://swcregistry.io/docs/SWC-118"],
            ))
    return findings


def detect_public_state_changing(source: str) -> List[Finding]:
    """Public state-changing functions without modifiers (no access control)."""
    findings = []
    pattern = re.compile(
        r"function\s+(?P<name>\w+)\s*\([^)]*\)\s+(?:public|external)"
        r"(?![^{]*(?:onlyOwner|onlyRole|view|pure|private|internal))[^{]*\{",
        re.DOTALL)
    for m in pattern.finditer(source):
        # Skip if it's view/pure
        head = m.group(0)
        if "view" in head or "pure" in head:
            continue
        name = m.group("name")
        if name.startswith("_") or name in ("constructor", "fallback", "receive"):
            continue
        # Heuristic: only flag setters / withdraw / mint / burn
        if not re.match(r"(set|withdraw|mint|burn|pause|unpause|init|upgrade)",
                        name, re.IGNORECASE):
            continue
        findings.append(_mk(
            title=f"Sensitive function `{name}` may lack access control",
            severity="high",
            desc="A public/external state-changing function appears to lack "
                 "an access-control modifier (e.g. onlyOwner, onlyRole).",
            source=source, line=_line_of(source, m.start()),
            recommendation="Add proper access control such as OpenZeppelin's "
                           "`Ownable` or `AccessControl`.",
            refs=["https://swcregistry.io/docs/SWC-105"],
        ))
    return findings


ALL_DETECTORS = [
    detect_tx_origin,
    detect_unchecked_low_level_call,
    detect_reentrancy_pattern,
    detect_pragma_floating,
    detect_block_timestamp,
    detect_selfdestruct,
    detect_missing_zero_check,
    detect_public_state_changing,
]


def run_all(source: str) -> List[Finding]:
    findings: List[Finding] = []
    for detector in ALL_DETECTORS:
        try:
            findings.extend(detector(source))
        except Exception as e:  # noqa: BLE001
            # Detector failures should not abort the audit
            print(f"[custom_detectors] {detector.__name__} failed: {e}")
    return findings


def detector_names() -> List[str]:
    return [d.__name__.replace("detect_", "") for d in ALL_DETECTORS]
