"""
Pure-Python Solidity call graph extractor.

Builds:
- Per-contract function nodes (id = "Contract.function") with visibility,
  modifier usage and source-line metadata.
- `call` edges between functions in the same / parent contract.
- `inheritance` edges between contracts (`is X, Y`).
- `modifier` edges from function -> modifier definition.

Heuristic only — no real AST. Good enough for visualization.
"""
import re
from typing import Dict, List, Optional, Tuple
from app.models.schemas import CallGraph, GraphNode, GraphEdge


SOLIDITY_BUILTINS = {
    "require", "assert", "revert", "keccak256", "sha256", "ripemd160",
    "ecrecover", "addmod", "mulmod", "blockhash", "selfdestruct", "suicide",
    "abi", "msg", "block", "tx", "this", "super", "address", "payable",
    "uint", "int", "bool", "string", "bytes", "type", "if", "for", "while",
    "do", "return", "emit", "new", "delete", "unchecked", "try", "catch",
}


def _find_balanced_block(source: str, open_idx: int) -> int:
    """Given index of '{', return index of the matching '}' (inclusive)."""
    depth = 0
    in_str: Optional[str] = None
    in_line_comment = False
    in_block_comment = False
    i = open_idx
    while i < len(source):
        ch = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
        elif in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 1
        elif in_str:
            if ch == "\\":
                i += 1
            elif ch == in_str:
                in_str = None
        else:
            if ch == "/" and nxt == "/":
                in_line_comment = True
                i += 1
            elif ch == "/" and nxt == "*":
                in_block_comment = True
                i += 1
            elif ch in ("'", '"'):
                in_str = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return -1  # unbalanced


def _line_of(source: str, idx: int) -> int:
    return source[:idx].count("\n") + 1


def _extract_contracts(source: str) -> List[Tuple[str, List[str], int, int]]:
    """
    Returns list of (name, inheritance_list, body_start, body_end).
    Includes contract / library / interface / abstract contract.
    """
    out = []
    pattern = re.compile(
        r"\b(?:abstract\s+)?(?:contract|library|interface)\s+(\w+)"
        r"(?:\s+is\s+(?P<inh>[^{]+))?\s*\{",
    )
    for m in pattern.finditer(source):
        name = m.group(1)
        inh_raw = m.group("inh") or ""
        # Strip generic args like Foo(uint x), keep just the name
        inh_list = [
            re.split(r"[\s(]", part.strip(), 1)[0]
            for part in inh_raw.split(",") if part.strip()
        ]
        body_open = m.end() - 1  # index of '{'
        body_close = _find_balanced_block(source, body_open)
        if body_close == -1:
            continue
        out.append((name, inh_list, body_open + 1, body_close))
    return out


_FN_PATTERN = re.compile(
    r"\bfunction\s+(?P<name>\w+)\s*\((?P<params>[^)]*)\)\s*"
    r"(?P<head>[^{;]*)(?:\{|;)",
    re.DOTALL,
)

_MOD_PATTERN = re.compile(
    r"\bmodifier\s+(?P<name>\w+)\s*(?:\([^)]*\))?\s*\{",
)

_CONSTRUCTOR_PATTERN = re.compile(
    r"\bconstructor\s*\((?P<params>[^)]*)\)\s*(?P<head>[^{]*)\{",
)


def _parse_function_modifiers(head: str) -> List[str]:
    """Extract modifier names from a function head (between args and body)."""
    head = re.sub(r"\b(public|external|internal|private|view|pure|payable|"
                  r"virtual|override|returns\s*\([^)]*\))\b", "", head)
    head = re.sub(r"\(.*?\)", "", head, flags=re.DOTALL)
    return [tok for tok in re.findall(r"\b\w+\b", head) if tok]


def _visibility_of(head: str) -> str:
    for vis in ("public", "external", "internal", "private"):
        if re.search(rf"\b{vis}\b", head):
            return vis
    return "internal"  # solidity default for functions


def _calls_in_body(body: str) -> List[str]:
    """Extract probable callees from a function body."""
    # Strip strings to avoid matching inside them
    body = re.sub(r'"(?:[^"\\]|\\.)*"', '""', body)
    body = re.sub(r"'(?:[^'\\]|\\.)*'", "''", body)
    callees = set()
    # Direct calls: name(  /  this.name(  /  super.name(  /  obj.name(
    for m in re.finditer(
            r"(?:\b(?:this|super)\s*\.\s*)?\b([A-Za-z_]\w*)\s*\(", body):
        name = m.group(1)
        if name in SOLIDITY_BUILTINS:
            continue
        # Skip type-cast-like uses: address( uint( etc handled by builtins
        callees.add(name)
    return sorted(callees)


def build(source: str) -> CallGraph:
    nodes: Dict[str, GraphNode] = {}
    edges: List[GraphEdge] = []
    contracts_info = _extract_contracts(source)
    contract_names = [c[0] for c in contracts_info]
    inheritance: Dict[str, List[str]] = {}

    # Track function and modifier names per contract for edge resolution
    fn_by_contract: Dict[str, List[str]] = {c: [] for c in contract_names}
    mod_by_contract: Dict[str, List[str]] = {c: [] for c in contract_names}

    # Pass 1: collect functions, constructors, modifiers
    for cname, inh, b_start, b_end in contracts_info:
        body = source[b_start:b_end]
        inheritance[cname] = inh

        for parent in inh:
            if parent in contract_names:
                edges.append(GraphEdge(
                    source=cname, target=parent, type="inheritance"))

        for cm in _CONSTRUCTOR_PATTERN.finditer(body):
            node_id = f"{cname}.<constructor>"
            line = _line_of(source, b_start + cm.start())
            nodes[node_id] = GraphNode(
                id=node_id,
                label="constructor",
                contract=cname,
                visibility="public",
                is_constructor=True,
                has_modifier=False,
                line=line,
            )
            fn_by_contract[cname].append("<constructor>")

        for fm in _FN_PATTERN.finditer(body):
            fn_name = fm.group("name")
            head = fm.group("head") or ""
            modifiers = _parse_function_modifiers(head)
            visibility = _visibility_of(head)
            node_id = f"{cname}.{fn_name}"
            line = _line_of(source, b_start + fm.start())
            nodes[node_id] = GraphNode(
                id=node_id,
                label=fn_name,
                contract=cname,
                visibility=visibility,
                is_constructor=False,
                has_modifier=bool(modifiers),
                line=line,
            )
            fn_by_contract[cname].append(fn_name)

            # Modifier edges (deferred resolution: we may not have seen the
            # modifier yet; resolve in pass 2)
            for mod in modifiers:
                edges.append(GraphEdge(
                    source=node_id,
                    target=f"{cname}.{mod}",  # may be re-targeted later
                    type="modifier",
                ))

        for mm in _MOD_PATTERN.finditer(body):
            mod_name = mm.group("name")
            node_id = f"{cname}.{mod_name}"
            line = _line_of(source, b_start + mm.start())
            nodes.setdefault(node_id, GraphNode(
                id=node_id,
                label=f"%{mod_name}",
                contract=cname,
                visibility="internal",
                is_constructor=False,
                has_modifier=False,
                line=line,
            ))
            mod_by_contract[cname].append(mod_name)

    # Pass 2: extract calls inside each function body and resolve edges.
    # Re-iterate functions to get bodies (we need start/end of each fn body).
    for cname, inh, b_start, b_end in contracts_info:
        body = source[b_start:b_end]

        # Iterate function definitions inside the contract body and find
        # each function's own body via balanced braces
        for fm in re.finditer(
                r"\bfunction\s+(?P<name>\w+)\s*\([^)]*\)\s*[^{;]*\{", body):
            fn_name = fm.group("name")
            fn_open_local = body.rfind("{", 0, fm.end())
            fn_open_global = b_start + fn_open_local
            fn_close_global = _find_balanced_block(source, fn_open_global)
            if fn_close_global == -1:
                continue
            fn_body = source[fn_open_global + 1:fn_close_global]
            src_id = f"{cname}.{fn_name}"
            for callee in _calls_in_body(fn_body):
                # Resolve callee:
                # 1) same-contract function
                if callee in fn_by_contract.get(cname, []):
                    edges.append(GraphEdge(
                        source=src_id,
                        target=f"{cname}.{callee}",
                        type="call",
                    ))
                    continue
                # 2) inherited function (any ancestor)
                resolved = None
                for parent in inh:
                    if callee in fn_by_contract.get(parent, []):
                        resolved = f"{parent}.{callee}"
                        break
                if resolved:
                    edges.append(GraphEdge(
                        source=src_id, target=resolved, type="call"))
                    continue
                # 3) cross-contract: try any contract that defines this fn
                for other, fns in fn_by_contract.items():
                    if other == cname:
                        continue
                    if callee in fns:
                        edges.append(GraphEdge(
                            source=src_id,
                            target=f"{other}.{callee}",
                            type="call",
                        ))
                        break
                # else: external / library / unresolved — skip silently

        # Same for constructors
        for cm in _CONSTRUCTOR_PATTERN.finditer(body):
            ctor_open = b_start + cm.end() - 1
            ctor_close = _find_balanced_block(source, ctor_open)
            if ctor_close == -1:
                continue
            ctor_body = source[ctor_open + 1:ctor_close]
            src_id = f"{cname}.<constructor>"
            for callee in _calls_in_body(ctor_body):
                if callee in fn_by_contract.get(cname, []):
                    edges.append(GraphEdge(
                        source=src_id,
                        target=f"{cname}.{callee}",
                        type="call",
                    ))

    # Drop modifier edges that point at non-existent nodes
    edges = [e for e in edges
             if e.type != "modifier" or e.target in nodes]

    # De-dup edges
    seen = set()
    unique_edges: List[GraphEdge] = []
    for e in edges:
        key = (e.source, e.target, e.type)
        if key in seen:
            continue
        seen.add(key)
        unique_edges.append(e)

    return CallGraph(
        nodes=list(nodes.values()),
        edges=unique_edges,
        contracts=contract_names,
        inheritance=inheritance,
    )
