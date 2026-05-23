"use client";
import { useEffect, useState } from "react";
import { CodeEditor } from "@/components/CodeEditor";
import { FindingsPanel } from "@/components/FindingsPanel";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { auditAddress, auditSource, exportReport, getHealth } from "@/lib/api";
import type { AuditReport } from "@/lib/types";
import { Download, Play, ShieldAlert, Wand2 } from "lucide-react";

const SAMPLE = `// Sample vulnerable contract for testing
pragma solidity ^0.8.0;

contract Vault {
    mapping(address => uint256) public balances;
    address public owner;

    constructor() { owner = msg.sender; }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // Vulnerable: reentrancy + unchecked call
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount);
        (bool ok,) = msg.sender.call{value: amount}("");
        balances[msg.sender] -= amount;
    }

    // Vulnerable: tx.origin auth + missing zero check
    function setOwner(address newOwner) external {
        require(tx.origin == owner);
        owner = newOwner;
    }

    function timeLottery() external view returns (uint) {
        return uint(blockhash(block.number - 1)) % block.timestamp;
    }
}
`;

type Tab = "source" | "address";

export default function Home() {
  const [tab, setTab] = useState<Tab>("source");
  const [source, setSource] = useState(SAMPLE);
  const [address, setAddress] = useState("");
  const [chain, setChain] = useState("eth");
  const [useSlither, setUseSlither] = useState(true);
  const [useAi, setUseAi] = useState(false);
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<AuditReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [slitherAvailable, setSlitherAvailable] = useState<boolean | null>(
    null
  );
  const [highlightLine, setHighlightLine] = useState<number | null>(null);

  useEffect(() => {
    getHealth()
      .then((h) => setSlitherAvailable(h.slither_available))
      .catch(() => setSlitherAvailable(false));
  }, []);

  async function runAudit() {
    setLoading(true);
    setError(null);
    setReport(null);
    try {
      let result: AuditReport;
      if (tab === "source") {
        result = await auditSource({
          source,
          use_slither: useSlither,
          use_ai: useAi,
        });
      } else {
        result = await auditAddress({
          address,
          chain,
          use_slither: useSlither,
          use_ai: useAi,
        });
        setSource(""); // address path: source is server-side
      }
      setReport(result);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function downloadReport(format: "markdown" | "json") {
    if (!report) return;
    const content = await exportReport(report, format);
    const blob = new Blob([content], {
      type: format === "json" ? "application/json" : "text/markdown",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit-report.${format === "json" ? "json" : "md"}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="min-h-screen p-6 max-w-[1600px] mx-auto">
      <header className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <ShieldAlert className="w-7 h-7 text-indigo-400" />
          <div>
            <h1 className="text-xl font-bold tracking-tight">
              Smart Contract Auditor
            </h1>
            <p className="text-xs text-gray-400">
              Static analysis & deep audit for Solidity
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span
            className={`px-2 py-1 rounded ${
              slitherAvailable
                ? "bg-green-500/20 text-green-300"
                : "bg-yellow-500/20 text-yellow-300"
            }`}
          >
            Slither: {slitherAvailable === null ? "…" : slitherAvailable ? "ready" : "unavailable"}
          </span>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="space-y-3">
          <div className="flex gap-2">
            <button
              className={`px-3 py-1.5 rounded text-sm ${
                tab === "source"
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-800 text-gray-300 hover:bg-gray-700"
              }`}
              onClick={() => setTab("source")}
            >
              Source Code
            </button>
            <button
              className={`px-3 py-1.5 rounded text-sm ${
                tab === "address"
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-800 text-gray-300 hover:bg-gray-700"
              }`}
              onClick={() => setTab("address")}
            >
              Contract Address
            </button>
          </div>

          {tab === "source" ? (
            <CodeEditor
              value={source}
              onChange={setSource}
              highlightLine={highlightLine}
            />
          ) : (
            <Card className="p-4 space-y-3">
              <label className="block text-sm text-gray-300">
                Contract Address
                <input
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="0x..."
                  className="mt-1 w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm font-mono"
                />
              </label>
              <label className="block text-sm text-gray-300">
                Chain
                <select
                  value={chain}
                  onChange={(e) => setChain(e.target.value)}
                  className="mt-1 w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm"
                >
                  <option value="eth">Ethereum</option>
                  <option value="bsc">BNB Smart Chain</option>
                  <option value="polygon">Polygon</option>
                  <option value="arbitrum">Arbitrum</option>
                </select>
              </label>
              <p className="text-xs text-gray-500">
                Source will be fetched from the corresponding block explorer.
                Backend must have an API key configured.
              </p>
            </Card>
          )}

          <Card className="p-4 flex flex-wrap items-center gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={useSlither}
                onChange={(e) => setUseSlither(e.target.checked)}
                disabled={!slitherAvailable}
              />
              Use Slither
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={useAi}
                onChange={(e) => setUseAi(e.target.checked)}
              />
              <Wand2 className="w-3 h-3" /> AI explanation
            </label>
            <div className="flex-1" />
            <Button onClick={runAudit} disabled={loading}>
              <Play className="w-4 h-4" />
              {loading ? "Auditing…" : "Run Audit"}
            </Button>
          </Card>

          {error && (
            <Card className="p-3 border-red-500/40 text-red-300 text-sm">
              {error}
            </Card>
          )}
        </section>

        <section className="space-y-3">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold">Findings</h2>
            {report && (
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  onClick={() => downloadReport("markdown")}
                >
                  <Download className="w-4 h-4" /> .md
                </Button>
                <Button variant="ghost" onClick={() => downloadReport("json")}>
                  <Download className="w-4 h-4" /> .json
                </Button>
              </div>
            )}
          </div>
          <FindingsPanel report={report} onJumpToLine={setHighlightLine} />
        </section>
      </div>
    </main>
  );
}
