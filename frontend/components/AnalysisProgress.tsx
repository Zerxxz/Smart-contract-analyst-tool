"use client";
import { useEffect, useState } from "react";
import { Sparkles, Search, Brain, FileCheck2, Check } from "lucide-react";

const STEPS = [
  { icon: Search, label: "Parsing contract" },
  { icon: Sparkles, label: "Running detectors" },
  { icon: Brain, label: "AI synthesizing report" },
  { icon: FileCheck2, label: "Finalizing" },
];

export function AnalysisProgress() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setActive((s) => (s + 1) % STEPS.length);
    }, 1400);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="glass-strong rounded-2xl p-8 animate-fade-up relative overflow-hidden">
      <div className="shimmer absolute inset-0 pointer-events-none" />
      <div className="flex items-center gap-3 mb-6">
        <span className="relative">
          <Sparkles className="w-5 h-5 text-indigo-400 pulse-ring rounded-full" />
        </span>
        <h3 className="font-semibold">Analyzing contract…</h3>
      </div>
      <div className="space-y-3">
        {STEPS.map((step, i) => {
          const Icon = step.icon;
          const isDone = i < active;
          const isActive = i === active;
          return (
            <div
              key={step.label}
              className="flex items-center gap-3 transition-opacity"
              style={{ opacity: isDone ? 0.6 : 1 }}
            >
              <span
                className={`flex items-center justify-center w-7 h-7 rounded-full transition-colors ${
                  isDone
                    ? "bg-emerald-500/20 text-emerald-300"
                    : isActive
                    ? "bg-indigo-500/20 text-indigo-300"
                    : "bg-white/5 text-gray-500"
                }`}
              >
                {isDone ? (
                  <Check className="w-3.5 h-3.5" />
                ) : (
                  <Icon className={`w-3.5 h-3.5 ${isActive ? "animate-pulse" : ""}`} />
                )}
              </span>
              <span
                className={`text-sm ${
                  isActive ? "text-white" : "text-gray-400"
                }`}
              >
                {step.label}
              </span>
              {isActive && (
                <span className="ml-auto text-xs text-indigo-300">working…</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
