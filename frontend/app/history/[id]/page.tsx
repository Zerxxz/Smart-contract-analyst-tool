"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { CodeEditor } from "@/components/CodeEditor";
import { FindingsPanel } from "@/components/FindingsPanel";
import { exportReport, getHistoryItem } from "@/lib/api";
import type { HistoryDetailResponse } from "@/lib/types";
import { ArrowLeft, Download } from "lucide-react";

export default function HistoryDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = Number(params?.id);
  const [detail, setDetail] = useState<HistoryDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [highlightLine, setHighlightLine] = useState<number | null>(null);

  useEffect(() => {
    if (!id) return;
    getHistoryItem(id).then(setDetail).catch((e) => setError(String(e)));
  }, [id]);

  async function download(format: "markdown" | "json" | "pdf") {
    if (!detail) return;
    const content = await exportReport(detail.report, format);
    let blob: Blob, ext: string;
    if (format === "pdf") {
      blob = content as Blob;
      ext = "pdf";
    } else if (format === "json") {
      blob = new Blob([content as string], { type: "application/json" });
      ext = "json";
    } else {
      blob = new Blob([content as string], { type: "text/markdown" });
      ext = "md";
    }
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit-${id}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (error)
    return (
      <main className="p-6 max-w-[1600px] mx-auto">
        <Card className="p-3 border-red-500/40 text-red-300 text-sm">{error}</Card>
      </main>
    );
  if (!detail)
    return (
      <main className="p-6 max-w-[1600px] mx-auto">
        <Card className="p-6 text-gray-400 text-sm">Loading…</Card>
      </main>
    );

  return (
    <main className="p-6 max-w-[1600px] mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => router.push("/history")}>
          <ArrowLeft className="w-4 h-4" /> Back
        </Button>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={() => download("markdown")}>
            <Download className="w-4 h-4" /> .md
          </Button>
          <Button variant="ghost" onClick={() => download("json")}>
            <Download className="w-4 h-4" /> .json
          </Button>
          <Button variant="ghost" onClick={() => download("pdf")}>
            <Download className="w-4 h-4" /> .pdf
          </Button>
        </div>
      </div>
      <header>
        <h1 className="text-xl font-bold tracking-tight">
          Audit #{detail.id} — {detail.report.meta.filename}
        </h1>
        <p className="text-xs text-gray-400">
          {new Date(detail.timestamp).toLocaleString()}
        </p>
      </header>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CodeEditor
          value={detail.source}
          onChange={() => {}}
          highlightLine={highlightLine}
        />
        <FindingsPanel
          report={detail.report}
          onJumpToLine={setHighlightLine}
        />
      </div>
    </main>
  );
}
