"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";
import {
  ShieldAlert, GitCompareArrows, Network, History as HistoryIcon, Flame,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "Audit", icon: ShieldAlert },
  { href: "/diff", label: "Diff", icon: GitCompareArrows },
  { href: "/graph", label: "Call Graph", icon: Network },
  { href: "/honeypot", label: "Honeypot", icon: Flame },
  { href: "/history", label: "History", icon: HistoryIcon },
];

export function Navigation() {
  const pathname = usePathname();
  return (
    <nav className="border-b border-[var(--border)] bg-[var(--panel)]">
      <div className="max-w-[1600px] mx-auto px-6 py-3 flex items-center gap-6">
        <Link href="/" className="flex items-center gap-2 text-sm font-bold">
          <ShieldAlert className="w-5 h-5 text-indigo-400" />
          <span>SC Auditor</span>
        </Link>
        <div className="flex items-center gap-1">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                  active
                    ? "bg-indigo-600 text-white"
                    : "text-gray-400 hover:bg-gray-800 hover:text-gray-200"
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
