"use client";
import { useState } from "react";
import type { AIAuditReport, KeyFinding, RiskLevel } from "@/lib/types";
import { SeverityBadge } from "./SeverityBadge";
import {
  ShieldCheck, AlertTriangle, Flame, Sparkles, ChevronDown,
  ChevronRight, Code2, Wrench, BookOpen, ListChecks, Brain,
  ExternalLink, Copy, Check,
} from "lucide-react";

const RISK_META: Record<RiskLevel, { label: string; color: string; ring: string; icon: any }> = {
  safe:           { label: "Safe",           color: "text-emerald-300", ring: "stroke-emerald-400", icon: ShieldCheck },
  low_risk:       { label: "Low risk",       color: "text-lime-300",    ring: "stroke-lime-400",    icon: ShieldCheck },
  moderate_risk:  { label: "Moderate risk",  color: "text-amber-300",   ring: "stroke-amber-400",   icon: AlertTriangle },
  high_risk:      { label: "High risk",      color: "text-orange-300",  ring: "stroke-orange-400",  icon: AlertTriangle },
  critical_risk:  { label: "Critical risk",  color: "text-red-300",     ring: "stroke-red-400",     icon: Flame },
};


export function AIReportView({ report }: { report: AIAuditReport }) {
  const meta = RISK_META[report.risk_level];
  const Icon = meta.icon;
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (report.overall_score / 100) * circumference;

  return (
    <div className="space-y-6 animate-fade-up">
      {/* Hero verdict ---------------------------------------------------- */}
      <section className="glass-strong rounded-2xl p-6 md:p-8">
        <div className="flex flex-col md:flex-row items-start md:items-center gap-6">
          {/* Score ring */}
          <div className="relative w-36 h-36 shrink-0">
            <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
              <circle
                cx="60" cy="60" r={radius}
                className="fill-none stroke-white/10"
                strokeWidth="8"
              />
              <circle
                cx="60" cy="60" r={radius}
                className={`fill-none ${meta.ring}`}
                strokeWidth="8"
                strokeDasharray={circumference}
                strokeDashoffset={offset}
                strokeLinecap="round"
                style={{ transition: "stroke-dashoffset 1s ease-out" }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <div className={`text-5xl font-bold ${meta.color}`}>
                {report.overall_score}
              </div>
              <div className="text-[10px] text-gray-400 uppercase tracking-wider">
                / 100
              </div>
            </div>
          </div>

          {/* Verdict */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <Icon className={`w-5 h-5 ${meta.color}`} />
              <span className={`text-xs uppercase tracking-wider font-semibold ${meta.color}`}>
                {meta.label}
              </span>
              {report.is_ai_generated ? (
                <span className="ml-auto flex items-center gap-1 text-[10px] uppercase tracking-wider text-indigo-300 bg-indigo-500/20 px-2 py-0.5 rounded-full">
                  <Brain className="w-3 h-3" /> AI-curated
                </span>
              ) : (
                <span className="ml-auto text-[10px] uppercase tracking-wider text-gray-500 bg-white/5 px-2 py-0.5 rounded-full">
                  template (add AI key for narrative)
                </span>
              )}
            </div>
            <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-white leading-tight">
              {report.one_line_verdict}
            </h2>
            <div className="mt-4 flex flex-wrap gap-4 text-xs text-gray-400">
              <Stat label="Contracts" value={report.raw_report.meta.contracts.join(", ") || "—"} />
              <Stat label="SLOC" value={String(report.raw_report.meta.sloc)} />
              <Stat label="Detectors" value={report.raw_report.meta.detectors_run.join(", ")} />
              <Stat label="Time" value={`${report.raw_report.meta.duration_ms} ms`} />
            </div>
          </div>
        </div>

        {/* Severity strip */}
        <div className="mt-6 grid grid-cols-5 gap-2">
          <SevPill label="Critical" count={report.raw_report.summary.critical} color="bg-red-500/15 text-red-300" />
          <SevPill label="High"     count={report.raw_report.summary.high}     color="bg-orange-500/15 text-orange-300" />
          <SevPill label="Medium"   count={report.raw_report.summary.medium}   color="bg-amber-500/15 text-amber-300" />
          <SevPill label="Low"      count={report.raw_report.summary.low}      color="bg-blue-500/15 text-blue-300" />
          <SevPill label="Info"     count={report.raw_report.summary.informational} color="bg-gray-500/15 text-gray-300" />
        </div>
      </section>

      {/* Executive summary ---------------------------------------------- */}
      <Section icon={BookOpen} title="Executive summary">
        <Markdown text={report.executive_summary} />
      </Section>

      {/* Honeypot strip (only if flagged) -------------------------------- */}
      {report.honeypot && report.honeypot.is_likely_honeypot && (
        <section className="glass-strong rounded-2xl p-5 border-red-500/30">
          <div className="flex items-center gap-3 mb-2">
            <Flame className="w-5 h-5 text-red-400" />
            <h3 className="font-semibold text-red-200">Honeypot warning</h3>
            <span className="ml-auto text-xs font-mono text-red-300">
              {report.honeypot.risk_score}/100
            </span>
          </div>
          <p className="text-sm text-gray-300">{report.honeypot.summary}</p>
        </section>
      )}

      {/* Key findings ---------------------------------------------------- */}
      <Section icon={Code2} title={`Key findings (${report.key_findings.length})`}>
        {report.key_findings.length === 0 ? (
          <div className="text-sm text-emerald-300 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4" />
            No issues identified.
          </div>
        ) : (
          <div className="space-y-3">
            {report.key_findings.map((kf, i) => (
              <KeyFindingCard key={i} idx={i + 1} kf={kf} />
            ))}
          </div>
        )}
      </Section>

      {/* Recommendations ------------------------------------------------- */}
      {report.recommendations.length > 0 && (
        <Section icon={ListChecks} title="Recommended actions">
          <ol className="space-y-2 list-decimal list-inside">
            {report.recommendations.map((r, i) => (
              <li key={i} className="text-sm text-gray-300">
                {r}
              </li>
            ))}
          </ol>
        </Section>
      )}

      {/* Code quality ---------------------------------------------------- */}
      {report.code_quality_notes && (
        <Section icon={Wrench} title="Code quality notes">
          <Markdown text={report.code_quality_notes} />
        </Section>
      )}
    </div>
  );
}

// ─── Sub-components ─────────────────────────────────────────────────────────

function Section({
  icon: Icon, title, children,
}: { icon: any; title: string; children: React.ReactNode }) {
  return (
    <section className="glass rounded-2xl p-5 md:p-6">
      <h3 className="flex items-center gap-2 font-semibold mb-3 text-gray-100">
        <Icon className="w-4 h-4 text-indigo-300" />
        {title}
      </h3>
      <div className="text-sm text-gray-300">{children}</div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-gray-500">
        {label}
      </div>
      <div className="text-xs text-gray-200 font-mono truncate max-w-[180px]">
        {value}
      </div>
    </div>
  );
}

function SevPill({
  label, count, color,
}: { label: string; count: number; color: string }) {
  return (
    <div className={`rounded-lg px-3 py-2 text-center ${color}`}>
      <div className="text-lg font-bold">{count}</div>
      <div className="text-[10px] uppercase tracking-wider">{label}</div>
    </div>
  );
}

function KeyFindingCard({ kf, idx }: { kf: KeyFinding; idx: number }) {
  const [open, setOpen] = useState(
    kf.severity === "critical" || kf.severity === "high"
  );
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--panel)]/60 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 p-4 text-left hover:bg-white/[0.02]"
      >
        {open ? (
          <ChevronDown className="w-4 h-4 shrink-0 text-gray-400" />
        ) : (
          <ChevronRight className="w-4 h-4 shrink-0 text-gray-400" />
        )}
        <span className="text-xs font-mono text-gray-500 w-6">#{idx}</span>
        <SeverityBadge severity={kf.severity} />
        <span className="font-semibold text-sm text-gray-100 flex-1 truncate">
          {kf.title}
        </span>
        <span className="text-xs text-gray-500 font-mono shrink-0">
          {kf.location}
        </span>
      </button>

      {open && (
        <div className="px-4 pb-5 border-t border-[var(--border)] pt-4 space-y-4 animate-fade-up">
          <Field label="Explanation" tone="indigo">
            <p className="text-sm text-gray-300">{kf.explanation}</p>
          </Field>

          <Field label="Impact" tone="red">
            <p className="text-sm text-gray-300">{kf.impact}</p>
          </Field>

          <Field label="Fix" tone="emerald">
            <p className="text-sm text-gray-300">{kf.fix}</p>
          </Field>

          {(kf.code_before || kf.code_after) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {kf.code_before && (
                <CodeBox
                  title="Before"
                  tone="red"
                  code={kf.code_before}
                />
              )}
              {kf.code_after && (
                <CodeBox
                  title="After (suggested)"
                  tone="emerald"
                  code={kf.code_after}
                />
              )}
            </div>
          )}

          {kf.references.length > 0 && (
            <div className="text-xs text-gray-400 space-y-1 pt-2 border-t border-[var(--border)]">
              {kf.references.map((r) => (
                <a
                  key={r}
                  href={r}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 hover:text-indigo-400"
                >
                  <ExternalLink className="w-3 h-3" /> {r}
                </a>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Field({
  label, tone, children,
}: {
  label: string;
  tone: "indigo" | "red" | "emerald";
  children: React.ReactNode;
}) {
  const color = {
    indigo: "text-indigo-300",
    red: "text-red-300",
    emerald: "text-emerald-300",
  }[tone];
  return (
    <div>
      <div className={`text-[10px] uppercase tracking-wider font-semibold ${color} mb-1`}>
        {label}
      </div>
      {children}
    </div>
  );
}

function CodeBox({
  title, tone, code,
}: {
  title: string;
  tone: "red" | "emerald";
  code: string;
}) {
  const [copied, setCopied] = useState(false);
  const headerColor = {
    red: "bg-red-500/10 text-red-300 border-red-500/30",
    emerald: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  }[tone];

  function copy() {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  return (
    <div className="rounded-lg border border-[var(--border)] overflow-hidden">
      <div className={`flex items-center justify-between px-3 py-1.5 text-[11px] font-semibold border-b ${headerColor}`}>
        <span>{title}</span>
        <button onClick={copy} className="hover:opacity-80 flex items-center gap-1">
          {copied ? (
            <><Check className="w-3 h-3" /> copied</>
          ) : (
            <><Copy className="w-3 h-3" /> copy</>
          )}
        </button>
      </div>
      <pre className="bg-black/40 p-3 text-xs font-mono overflow-x-auto text-gray-200 whitespace-pre">
{code}
      </pre>
    </div>
  );
}

// ─── Tiny markdown renderer for AI text (bold, code, line breaks) ───────────
function Markdown({ text }: { text: string }) {
  const lines = text.split("\n");
  return (
    <div className="space-y-2 leading-relaxed">
      {lines.map((line, i) => {
        if (!line.trim()) return null;
        if (line.startsWith("- ")) {
          return (
            <div key={i} className="flex gap-2">
              <span className="text-indigo-300">•</span>
              <span dangerouslySetInnerHTML={{ __html: inlineMd(line.slice(2)) }} />
            </div>
          );
        }
        return (
          <p key={i} dangerouslySetInnerHTML={{ __html: inlineMd(line) }} />
        );
      })}
    </div>
  );
}

function inlineMd(s: string): string {
  // Escape HTML, then apply small subset of markdown
  let out = s
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
  out = out.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  out = out.replace(/`([^`]+)`/g, '<code class="px-1 py-0.5 rounded bg-white/5 text-indigo-200 font-mono text-[12px]">$1</code>');
  return out;
}
