"""
Slither integration via subprocess. Gracefully degrades if Slither is not
installed — custom detectors will still run.
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
    "Optimization": "informational",
}


def is_available() -> bool:
    return shutil.which("slither") is not None


def run(source: str, filename: str = "Contract.sol",
        solc_version: Optional[str] = None) -> List[Finding]:
    if not is_available():
        return []

    findings: List[Finding] = []
    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, filename)
        with open(src_path, "w", encoding="utf-8") as f:
            f.write(source)

        out_path = os.path.join(tmp, "slither.json")
        cmd = ["slither", src_path, "--json", out_path]
        env = os.environ.copy()
        if solc_version:
            # Use solc-select if available
            try:
                subprocess.run(["solc-select", "use", solc_version],
                               check=False, env=env, timeout=30)
            except Exception:
                pass

        try:
            subprocess.run(cmd, env=env, capture_output=True,
                           timeout=120, check=False)
        except subprocess.TimeoutExpired:
            return [Finding(
                id=str(uuid.uuid4())[:8],
                title="Slither analysis timed out",
                severity="informational",
                description="Slither did not complete within 120s.",
                detector="slither",
            )]

        if not os.path.exists(out_path):
            return findings

        try:
            with open(out_path) as f:
                data = json.load(f)
        except json.JSONDecodeError:
            return findings

        for det in data.get("results", {}).get("detectors", []):
            elements = det.get("elements", [])
            line_start = None
            line_end = None
            file_name = None
            if elements:
                src_map = elements[0].get("source_mapping", {})
                lines = src_map.get("lines", [])
                if lines:
                    line_start = lines[0]
                    line_end = lines[-1]
                file_name = src_map.get("filename_short")

            findings.append(Finding(
                id=str(uuid.uuid4())[:8],
                title=det.get("check", "slither finding"),
                severity=SEVERITY_MAP.get(det.get("impact", "Low"), "low"),
                description=det.get("description", "").strip(),
                detector="slither",
                file=file_name,
                line_start=line_start,
                line_end=line_end,
                recommendation="See Slither documentation for `"
                               f"{det.get('check')}`.",
                references=[
                    "https://github.com/crytic/slither/wiki/Detector-Documentation"
                    f"#{det.get('check', '').replace('-', '')}"
                ],
            ))
    return findings
