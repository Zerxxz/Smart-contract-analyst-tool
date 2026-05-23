"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { deleteHistoryItem, listHistory } from "@/lib/api";
import type { HistoryEntry } from "@/lib/types";
import { History as HistoryIcon, Trash2, Eye } from "lucide-react";

export default function HistoryPage() {
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const r = await listHistory(100, 0);
      setEntries(r.entries);
      setTotal(r.total);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function onDelete(id: number) {
    if (!confirm(`Delete audit #${id}?`)) return;
    try {
      await deleteHistoryItem(id);
      setEntries((es) => es.filter((e) => e.id !== id));
      setTotal((t) => t - 1);
    } catch (e) {
      alert((e as Error).message);
    }
  }

  return (
    <main className="p-6 max-w-[1600px] mx-auto">
      <header className="mb-6 flex items-center gap-3">
        <HistoryIcon className="w-6 h-6 text-indigo-400" />
        <div>
          <h1 className="text-xl font-bold tracking-tight">Audit History</h1>
          <p className="text-xs text-gray-400">
            {total} saved audit{total === 1 ? "" : "s"}. Enable
            <span className="font-mono text-indigo-300"> Save to history </span>
            on the Audit page to persist a run.
          </p>
        </div>
      </header>

      {loading ? (
        <Card className="p-6 text-gray-400 text-sm">Loading…</Card>
      ) : error ? (
        <Card className="p-3 border-red-500/40 text-red-300 text-sm">{error}</Card>
      ) : entries.length === 0 ? (
        <Card className="p-6 text-gray-400 text-sm">
          No history yet. Run an audit with{" "}
          <span className="font-mono">persist</span> enabled to populate this list.
        </Card>
      ) : (
        <div className="space-y-2">
          {entries.map((e) => (
            <Card
              key={e.id}
              className="p-4 flex items-center gap-4 hover:bg-gray-800/30"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-gray-500 font-mono">#{e.id}</span>
                  <span className="font-semibold truncate">{e.filename}</span>
                  {e.contracts.slice(0, 3).map((c) => (
                    <span
                      key={c}
                      className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono"
                    >
                      {c}
                    </span>
                  ))}
                </div>
                <div className="text-[11px] text-gray-500 mt-1">
                  {new Date(e.timestamp).toLocaleString()} · SLOC {e.sloc} ·{" "}
                  detectors: {e.detectors_run.join(", ")}
                </div>
              </div>
              <div className="flex gap-2 text-[11px]">
                <Pill color="red" count={e.summary.critical}>C</Pill>
                <Pill color="orange" count={e.summary.high}>H</Pill>
                <Pill color="yellow" count={e.summary.medium}>M</Pill>
                <Pill color="blue" count={e.summary.low}>L</Pill>
                <Pill color="gray" count={e.summary.informational}>I</Pill>
              </div>
              <div className="flex gap-2 shrink-0">
                <Link href={`/history/${e.id}`}>
                  <Button variant="ghost">
                    <Eye className="w-4 h-4" />
                  </Button>
                </Link>
                <Button variant="ghost" onClick={() => onDelete(e.id)}>
                  <Trash2 className="w-4 h-4 text-red-400" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </main>
  );
}

function Pill({
  color, count, children,
}: {
  color: "red" | "orange" | "yellow" | "blue" | "gray";
  count: number;
  children: React.ReactNode;
}) {
  const cls = {
    red: "bg-red-500/20 text-red-300",
    orange: "bg-orange-500/20 text-orange-300",
    yellow: "bg-yellow-500/20 text-yellow-300",
    blue: "bg-blue-500/20 text-blue-300",
    gray: "bg-gray-500/20 text-gray-300",
  }[color];
  return (
    <span className={`px-2 py-0.5 rounded font-mono ${cls}`}>
      {children}:{count}
    </span>
  );
}
