import type { Severity } from "@/lib/types";
import { cn } from "@/lib/cn";

const styles: Record<Severity, string> = {
  critical: "bg-red-500/20 text-red-300 border-red-500/40",
  high: "bg-orange-500/20 text-orange-300 border-orange-500/40",
  medium: "bg-yellow-500/20 text-yellow-300 border-yellow-500/40",
  low: "bg-blue-500/20 text-blue-300 border-blue-500/40",
  informational: "bg-gray-500/20 text-gray-300 border-gray-500/40",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={cn(
        "px-2 py-0.5 rounded text-xs font-semibold uppercase border",
        styles[severity]
      )}
    >
      {severity}
    </span>
  );
}
