"""
Mythril symbolic execution integration via subprocess.

Mythril is heavyweight (z3-solver) and can take several minutes on real
contracts. This wrapper:
- Detects availability gracefully (no crash if not installed)
- Sets a hard timeout
- Parses Mythril JSON output into our Finding schema
"""
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from typing import List, Optional
from app.models.schemas import Finding


SEVERITY_MAP = {
    "High": "high",
    "Medium": "medium",
    "Low": "low",
    "Informational": "informational",
}


def is_available() -> bool:
    return shutil.which("myth") is not None


def run(source: str, filename: str = "Contract.sol",
        solc_version: Optional[str] = None,
        timeout_sec: int = 180,
        max_depth: int = 12) -> List[Finding]:
    if not is_available():
        return []

    findings: List[Finding] = []

    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, filename)
        with open(src_path, "w", encoding="utf-8") as f:
            f.write(source)

        env = os.environ.copy()
        if solc_version:
            try:
                subprocess.run(["solc-select", "use", solc_version],
                               check=False, env=env, timeout=30)
            except Exception:
                pass

        cmd = [
            "myth", "analyze", src_path,
            "-o", "json",
            "--max-depth", str(max_depth),
            "--execution-timeout", str(timeout_sec - 10),
        ]
        try:
            proc = subprocess.run(
                cmd, env=env, capture_output=True,
                timeout=timeout_sec, check=False,
            )
        except subprocess.TimeoutExpired:
            return [Finding(
                id=str(uuid.uuid4())[:8],
                title="Mythril analysis timed out",
                severity="informational",
                description=f"Mythril did not complete within {timeout_sec}s. "
                            "Try shorter analysis depth or run on a smaller "
                            "subset of the contract.",
                detector="mythril",
            )]

        # Mythril returns non-zero exit code if it finds issues — that's
        # expected and not an error.
        stdout = proc.stdout.decode("utf-8", errors="replace")

        # Mythril sometimes prefixes JSON with log lines; locate the first {
        brace_idx = stdout.find("{")
        if brace_idx == -1:
            return findings
        json_text = stdout[brace_idx:]

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            # Take only the first JSON object greedily
            depth = 0
            end = -1
            for i, ch in enumerate(json_text):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end == -1:
                return findings
            try:
                data = json.loads(json_text[:end])
            except json.JSONDecodeError:
                return findings

        issues = data.get("issues", []) if isinstance(data, dict) else []
        if not issues and isinstance(data, dict) and data.get("success"):
            return findings

        for issue in issues:
            severity = SEVERITY_MAP.get(issue.get("severity", "Low"), "low")
            swc_id = issue.get("swc-id", "")
            refs = []
            if swc_id:
                refs.append(f"https://swcregistry.io/docs/SWC-{swc_id}")
            refs.append("https://mythril-classic.readthedocs.io")

            findings.append(Finding(
                id=str(uuid.uuid4())[:8],
                title=issue.get("title", "Mythril issue"),
                severity=severity,
                description=issue.get("description", "").strip()[:1500],
                detector="mythril",
                file=filename,
                line_start=issue.get("lineno"),
                line_end=issue.get("lineno"),
                recommendation=(
                    "Review the affected function. Consider adding "
                    "invariants or refactoring the affected code path."
                ),
                references=refs,
            ))
    return findings
