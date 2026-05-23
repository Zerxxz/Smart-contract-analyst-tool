"use client";
import { useEffect, useRef, useState } from "react";
import { CodeEditor } from "@/components/CodeEditor";
import { Button } from "@/components/ui/Button";
import { AIReportView } from "@/components/AIReportView";
import { AnalysisProgress } from "@/components/AnalysisProgress";
import { aiAudit, exportReport, getHealth } from "@/lib/api";
import type { AIAuditReport } from "@/lib/types";
import {
  Sparkles, ArrowRight, Download, RefreshCw, Code, Brain,
  Save,
} from "lucide-react";

const SAMPLE = `// Paste any Solidity contract here
pragma solidity ^0.8.0;

contract Vault {
    mapping(address => uint256) public balances;
    address public owner;

    constructor() { owner = msg.sender; }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount);
        (bool ok,) = msg.sender.call{value: amount}("");
        balances[msg.sender] -= amount;
    }

    function setOwner(address newOwner) external {
        require(tx.origin == owner);
        owner = newOwner;
    }
}
`;

export default function Home() {
  const [source, setSource] = useState(SAMPLE);
  const [report, setReport] = useState<AIAuditReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [persist, setPersist] = useState(false);
  const [aiConfigured, setAiConfigured] = useState<boolean | null>(null);
  const reportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getHealth()
      .then((h) => setAiConfigured(h.ai_configured))
      .catch(() => setAiConfigured(false));
  }, []);

  async function analyze() {
    if (!source.trim()) {
      setError("Please paste a contract first.");
      return;
    }
    setLoading(true);
    setError(null);
    setReport(null);
    try {
      const r = await aiAudit({ source, persist });
      setReport(r);
      // Smooth scroll to report
      setTimeout(() => {
        reportRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }, 100);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function download(format: "markdown" | "json" | "pdf") {
    if (!report) return;
    const content = await exportReport(report.raw_report, format);
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
    a.download = `audit-report.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function reset() {
    setReport(null);
    setError(null);
  }

  return (
    <main className="aurora-bg min-h-screen">
      {/* HERO + INPUT --------------------------------------------------- */}
      <section className="max-w-5xl mx-auto px-6 pt-12 md:pt-20 pb-10">
        <div className="text-center mb-10 animate-fade-up">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full glass mb-5">
            <Sparkles className="w-3.5 h-3.5 text-indigo-300" />
            <span className="text-xs font-medium text-gray-200 tracking-wide">
              AI-curated smart contract audit
            </span>
            {aiConfigured === false && (
              <span className="text-[10px] uppercase tracking-wider text-amber-300 ml-1">
                · template mode
              </span>
            )}
          </div>
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight leading-[1.05]">
            <span className="text-gradient">Audit any Solidity contract</span>
            <br />
            <span className="text-white">in seconds.</span>
          </h1>
          <p className="mt-5 text-base md:text-lg text-gray-400 max-w-2xl mx-auto">
            Paste your contract below, click <strong className="text-gray-200">Analyze</strong>,
            and get a clean, executive-quality report with prioritized fixes.
          </p>
        </div>

        {/* Input card */}
        <div className="glass-strong rounded-2xl p-1.5 animate-fade-up" style={{ animationDelay: "0.1s" }}>
          <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--border)]">
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <Code className="w-3.5 h-3.5" />
              <span className="font-mono">Contract.sol</span>
            </div>
            <button
              onClick={() => setSource("")}
              className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
            >
              Clear
            </button>
          </div>
          <div className="rounded-b-xl overflow-hidden">
            <CodeEditor value={source} onChange={setSource} />
          </div>
        </div>

        <div className="mt-5 flex flex-col sm:flex-row items-center gap-3 justify-center animate-fade-up" style={{ animationDelay: "0.2s" }}>
          <button
            onClick={analyze}
            disabled={loading}
            className="btn-gradient inline-flex items-center gap-2 px-7 py-3 rounded-xl font-semibold text-base"
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Analyzing…
              </>
            ) : (
              <>
                <Brain className="w-4 h-4" />
                Analyze contract
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>

          <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={persist}
              onChange={(e) => setPersist(e.target.checked)}
              className="accent-indigo-500"
            />
            <Save className="w-3.5 h-3.5" />
            Save to history
          </label>
        </div>

        {error && (
          <div className="mt-5 max-w-xl mx-auto rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200 animate-fade-up">
            {error}
          </div>
        )}
      </section>

      {/* RESULTS -------------------------------------------------------- */}
      <section
        ref={reportRef}
        className="max-w-5xl mx-auto px-6 pb-20"
      >
        {loading && <AnalysisProgress />}

        {report && !loading && (
          <>
            <div className="flex items-center justify-between mb-5 animate-fade-up">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                Audit report
              </h2>
              <div className="flex items-center gap-2">
                <Button variant="ghost" onClick={() => download("markdown")}>
                  <Download className="w-3.5 h-3.5" /> .md
                </Button>
                <Button variant="ghost" onClick={() => download("json")}>
                  <Download className="w-3.5 h-3.5" /> .json
                </Button>
                <Button variant="ghost" onClick={() => download("pdf")}>
                  <Download className="w-3.5 h-3.5" /> .pdf
                </Button>
                <Button variant="ghost" onClick={reset}>
                  <RefreshCw className="w-3.5 h-3.5" /> New
                </Button>
              </div>
            </div>
            <AIReportView report={report} />
          </>
        )}

        {!report && !loading && !error && (
          <FeatureRow />
        )}
      </section>
    </main>
  );
}

function FeatureRow() {
  const items = [
    {
      title: "8 custom heuristics",
      body: "Reentrancy, tx.origin, selfdestruct, access-control, unchecked calls, and more.",
    },
    {
      title: "Mempool & MEV",
      body: "Slippage, sandwich, spot-price oracle, ERC-4626 inflation, approve-race.",
    },
    {
      title: "Honeypot scanner",
      body: "9 indicators with 0–100 risk score: tax, blacklist, transfer-restriction.",
    },
    {
      title: "AI-curated report",
      body: "Executive summary, prioritized fixes, before/after code, references.",
    },
  ];
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-4 animate-fade-up">
      {items.map((it) => (
        <div key={it.title} className="glass rounded-xl p-4">
          <div className="text-sm font-semibold text-gray-100 mb-1">
            {it.title}
          </div>
          <p className="text-xs text-gray-400 leading-relaxed">{it.body}</p>
        </div>
      ))}
    </div>
  );
}
