"use client";
import type { HoneypotReport } from "@/lib/types";
import { Card } from "./ui/Card";
import { SeverityBadge } from "./SeverityBadge";
import { Flame, ShieldCheck, AlertTriangle } from "lucide-react";

export function HoneypotPanel({ report }: { report: HoneypotReport | null }) {
  if (!report) return null;

  const score = report.risk_score;
  const tone =
    score >= 70 ? "danger" : score >= 40 ? "warning" : "safe";
  const ringColor = {
    danger: "stroke-red-500",
    warning: "stroke-orange-400",
    safe: "stroke-green-500",
  }[tone];
  const Icon = tone === "danger" ? Flame : tone === "warning" ? AlertTriangle : ShieldCheck;
  const headerText = report.is_likely_honeypot
    ? "Likely honeypot"
    : score === 0
    ? "No honeypot indicators"
    : "Some indicators detected";

  // Score ring math
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <Card className="p-5 space-y-4">
      <div className="flex items-center gap-4">
        <div className="relative w-24 h-24 shrink-0">
          <svg className="w-full h-full -rotate-90" viewBox="0 0 80 80">
            <circle
              cx="40" cy="40" r={radius}
              className="stroke-gray-700 fill-none" strokeWidth="6"
            />
            <circle
              cx="40" cy="40" r={radius}
              className={`fill-none ${ringColor}`}
              strokeWidth="6"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-bold">{score}</span>
            <span className="text-[10px] text-gray-400 uppercase">/ 100</span>
          </div>
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Icon className={`w-5 h-5 ${
              tone === "danger" ? "text-red-400" :
              tone === "warning" ? "text-orange-400" :
              "text-green-400"
            }`} />
            <h3 className="text-base font-semibold">{headerText}</h3>
          </div>
          <p className="text-sm text-gray-400">{report.summary}</p>
        </div>
      </div>

      {report.indicators.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs uppercase text-gray-500 font-semibold">
            Indicators ({report.indicators.length})
          </div>
          {report.indicators.map((ind, i) => (
            <div
              key={`${ind.name}-${i}`}
              className="border border-[var(--border)] rounded p-3 space-y-1"
            >
              <div className="flex items-start gap-2">
                <SeverityBadge severity={ind.severity} />
                <span className="font-semibold text-sm flex-1">{ind.name}</span>
                {ind.line && (
                  <span className="text-xs text-gray-500 font-mono">L{ind.line}</span>
                )}
              </div>
              <p className="text-xs text-gray-400">{ind.description}</p>
              {ind.evidence && (
                <pre className="text-xs bg-black/40 rounded p-2 font-mono overflow-x-auto text-gray-300">
                  {ind.evidence}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
