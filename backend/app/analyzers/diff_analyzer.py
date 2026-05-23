"""
Diff audit: compare two versions of a contract, run audit on each, then
report findings that were introduced or fixed.
"""
import difflib
from typing import List, Tuple
from app.models.schemas import (
    Finding, AuditReport, DiffResult, DiffFindingDelta,
)


def _fingerprint(f: Finding) -> str:
    """
    Stable fingerprint for matching findings across versions.
    Lines may shift between versions, so we omit them and rely on title +
    severity + detector + a normalized snippet of the code around it.
    """
    snippet = (f.code_snippet or "").strip()
    # Normalize whitespace
    snippet = " ".join(snippet.split())
    # Drop the leading line numbers we render in code_snippet
    snippet = " ".join(
        part for part in snippet.split() if not part.isdigit()
        and part != "|"
    )
    return f"{f.detector}::{f.severity}::{f.title}::{snippet[:80]}"


def compute_delta(old: List[Finding],
                  new: List[Finding]) -> Tuple[List[Finding], List[Finding], int]:
    old_map = {_fingerprint(f): f for f in old}
    new_map = {_fingerprint(f): f for f in new}

    old_keys = set(old_map)
    new_keys = set(new_map)

    removed = [old_map[k] for k in old_keys - new_keys]
    added = [new_map[k] for k in new_keys - old_keys]
    unchanged = len(old_keys & new_keys)
    return added, removed, unchanged


def make_diff(source_old: str, source_new: str,
              filename: str) -> Tuple[str, int, int]:
    """Returns (unified_diff_text, lines_added, lines_removed)."""
    old_lines = source_old.splitlines(keepends=True)
    new_lines = source_new.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        n=3,
    )
    diff_text = "".join(diff)
    added = sum(1 for line in diff_text.splitlines()
                if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff_text.splitlines()
                  if line.startswith("-") and not line.startswith("---"))
    return diff_text, added, removed


def build_diff_result(source_old: str, source_new: str, filename: str,
                      old_report: AuditReport,
                      new_report: AuditReport) -> DiffResult:
    diff_text, added_lines, removed_lines = make_diff(
        source_old, source_new, filename)
    added_findings, removed_findings, unchanged_count = compute_delta(
        old_report.findings, new_report.findings)
    return DiffResult(
        unified_diff=diff_text,
        lines_added=added_lines,
        lines_removed=removed_lines,
        old_report=old_report,
        new_report=new_report,
        delta=DiffFindingDelta(
            added=added_findings,
            removed=removed_findings,
            unchanged_count=unchanged_count,
        ),
    )
