"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";
import {
  GitCompareArrows, Network, History as HistoryIcon, Flame, Sparkles,
} from "lucide-react";

const ADVANCED = [
  { href: "/diff", label: "Diff", icon: GitCompareArrows },
  { href: "/graph", label: "Graph", icon: Network },
  { href: "/honeypot", label: "Honeypot", icon: Flame },
  { href: "/history", label: "History", icon: HistoryIcon },
];

export function Navigation() {
  const pathname = usePathname();
  return (
    <nav className="sticky top-0 z-50 border-b border-[var(--border)] bg-[var(--bg)]/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-6">
        <Link
          href="/"
          className="flex items-center gap-2 text-sm font-bold tracking-tight"
        >
          <span className="relative">
            <Sparkles className="w-5 h-5 text-indigo-400" />
            <span className="absolute -inset-1 bg-indigo-500/30 blur-md rounded-full -z-10" />
          </span>
          <span className="text-gradient">SC Auditor</span>
        </Link>

        <Link
          href="/"
          className={cn(
            "px-3 py-1.5 rounded-md text-xs font-medium",
            pathname === "/"
              ? "bg-white/10 text-white"
              : "text-gray-400 hover:bg-white/5 hover:text-gray-200"
          )}
        >
          Audit
        </Link>

        <div className="h-4 w-px bg-[var(--border)]" />

        <div className="flex items-center gap-1">
          <span className="text-[10px] uppercase tracking-wider text-gray-500 mr-2">
            Advanced
          </span>
          {ADVANCED.map(({ href, label, icon: Icon }) => {
            const active = pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium",
                  active
                    ? "bg-white/10 text-white"
                    : "text-gray-400 hover:bg-white/5 hover:text-gray-200"
                )}
              >
                <Icon className="w-3.5 h-3.5" />
                {label}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
