"use client";
import { cn } from "@/lib/cn";

export function DiffViewer({ diff }: { diff: string }) {
  if (!diff.trim()) {
    return (
      <div className="text-center text-sm text-gray-400 py-6">
        No changes detected.
      </div>
    );
  }
  const lines = diff.split("\n");
  return (
    <pre className="text-xs font-mono bg-black/40 rounded-lg overflow-x-auto p-0">
      {lines.map((line, i) => {
        let className = "px-3 py-0.5 text-gray-300";
        if (line.startsWith("+++") || line.startsWith("---")) {
          className = "px-3 py-0.5 text-gray-500 font-semibold";
        } else if (line.startsWith("@@")) {
          className = "px-3 py-0.5 text-indigo-400 bg-indigo-500/10";
        } else if (line.startsWith("+")) {
          className = "px-3 py-0.5 text-green-300 bg-green-500/10";
        } else if (line.startsWith("-")) {
          className = "px-3 py-0.5 text-red-300 bg-red-500/10";
        }
        return (
          <div key={i} className={cn(className, "whitespace-pre")}>
            {line || " "}
          </div>
        );
      })}
    </pre>
  );
}
