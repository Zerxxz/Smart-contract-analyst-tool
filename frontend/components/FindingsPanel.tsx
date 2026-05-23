"use client";
import { useState } from "react";
import type { AuditReport, Finding } from "@/lib/types";
import { SeverityBadge } from "./SeverityBadge";
import { Card } from "./ui/Card";
import { cn } from "@/lib/cn";
import { ChevronDown, ChevronRight, ExternalLink, FileText } from "lucide-react";

interface Props {
  report: AuditReport | null;
  onJumpToLine?: (line: number) => void;
}

export function FindingsPanel({ report, onJumpToLine }: Props) {
  if (!report) {
    return (
      <Card className="p-6 text-gray-400 text-sm">
        Run an audit to see findings here.
      </Card>
    );
  }

  const { meta, findings, summary } = report;

  return (
    <div className="space-y-4">
      <Card className="p-4">
        <div className="flex flex-wrap gap-4 text-sm">
          <Stat label="File" value={meta.filename} />
          <Stat label="SLOC" value={String(meta.sloc)} />
          <Stat
            label="Contracts"
            value={meta.contracts.join(", ") || "—"}
          />
          <Stat
            label="Detectors"
            value={meta.detectors_run.join(", ")}
          />
          <Stat label="Time" value={`${meta.duration_ms} ms`} />
        </div>
        <div className="mt-3 flex gap-2 flex-wrap">
          <SummaryPill label="Critical" count={summary.critical} sev="critical" />
          <SummaryPill label="High" count={summary.high} sev="high" />
          <SummaryPill label="Medium" count={summary.medium} sev="medium" />
          <SummaryPill label="Low" count={summary.low} sev="low" />
          <SummaryPill label="Info" count={summary.informational} sev="informational" />
        </div>
      </Card>

      {findings.length === 0 ? (
        <Card className="p-6 text-center text-green-400">
          ✅ No findings — clean run.
        </Card>
      ) : (
        findings.map((f) => (
          <FindingCard key={f.id} finding={f} onJumpToLine={onJumpToLine} />
        ))
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase text-gray-500">{label}</div>
      <div className="text-sm text-gray-200 font-mono truncate max-w-xs">
        {value}
      </div>
    </div>
  );
}

function SummaryPill({
  label,
  count,
  sev,
}: {
  label: string;
  count: number;
  sev: string;
}) {
  const color: Record<string, string> = {
    critical: "bg-red-500/20 text-red-300",
    high: "bg-orange-500/20 text-orange-300",
    medium: "bg-yellow-500/20 text-yellow-300",
    low: "bg-blue-500/20 text-blue-300",
    informational: "bg-gray-500/20 text-gray-300",
  };
  return (
    <div
      className={cn(
        "px-2.5 py-1 rounded-md text-xs font-semibold",
        color[sev]
      )}
    >
      {label}: {count}
    </div>
  );
}

function FindingCard({
  finding,
  onJumpToLine,
}: {
  finding: Finding;
  onJumpToLine?: (line: number) => void;
}) {
  const [open, setOpen] = useState(
    finding.severity === "critical" || finding.severity === "high"
  );
  return (
    <Card>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 p-4 text-left hover:bg-gray-800/40"
      >
        {open ? (
          <ChevronDown className="w-4 h-4 shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 shrink-0" />
        )}
        <SeverityBadge severity={finding.severity} />
        <span className="font-semibold text-gray-100 flex-1">
          {finding.title}
        </span>
        <span className="text-xs text-gray-500 font-mono">
          {finding.detector}
        </span>
        {finding.line_start && (
          <span
            onClick={(e) => {
              e.stopPropagation();
              onJumpToLine?.(finding.line_start!);
            }}
            className="text-xs text-indigo-400 hover:underline font-mono cursor-pointer"
          >
            L{finding.line_start}
          </span>
        )}
      </button>
      {open && (
        <div className="px-4 pb-4 border-t border-[var(--border)] pt-3 space-y-3">
          <p className="text-sm text-gray-300">{finding.description}</p>
          {finding.code_snippet && (
            <pre className="bg-black/40 rounded p-3 text-xs overflow-x-auto font-mono text-gray-300">
              {finding.code_snippet}
            </pre>
          )}
          {finding.recommendation && (
            <div className="text-sm">
              <span className="text-green-400 font-semibold">
                Recommendation:{" "}
              </span>
              <span className="text-gray-300">{finding.recommendation}</span>
            </div>
          )}
          {finding.ai_explanation && (
            <div className="bg-indigo-500/10 border border-indigo-500/30 rounded p-3">
              <div className="text-xs uppercase text-indigo-300 font-semibold mb-1">
                AI Analysis
              </div>
              <p className="text-sm text-gray-200 whitespace-pre-wrap">
                {finding.ai_explanation}
              </p>
            </div>
          )}
          {finding.references.length > 0 && (
            <div className="text-xs text-gray-400 space-y-1">
              {finding.references.map((r) => (
                <a
                  key={r}
                  href={r}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 hover:text-indigo-400"
                >
                  <ExternalLink className="w-3 h-3" />
                  {r}
                </a>
              ))}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
