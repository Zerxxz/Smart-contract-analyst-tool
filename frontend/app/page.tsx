"use client";
import { useEffect, useState } from "react";
import { CodeEditor } from "@/components/CodeEditor";
import { FindingsPanel } from "@/components/FindingsPanel";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import {
  auditAddress, auditSource, exportReport, getHealth, honeypotSource,
} from "@/lib/api";
import type { AuditReport, HoneypotReport } from "@/lib/types";
import { Download, Play, Wand2, Save, Flame } from "lucide-react";
import { HoneypotPanel } from "@/components/HoneypotPanel";

const SAMPLE = `// Sample vulnerable contract for testing
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

type Tab = "source" | "address";

export default function Home() {
  const [tab, setTab] = useState<Tab>("source");
  const [source, setSource] = useState(SAMPLE);
  const [address, setAddress] = useState("");
  const [chain, setChain] = useState("eth");

  const [useSlither, setUseSlither] = useState(true);
  const [useMythril, setUseMythril] = useState(false);
  const [useMempool, setUseMempool] = useState(true);
  const [useHoneypot, setUseHoneypot] = useState(true);
  const [useAi, setUseAi] = useState(false);
  const [persist, setPersist] = useState(false);

  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<AuditReport | null>(null);
  const [honeypotReport, setHoneypotReport] = useState<HoneypotReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [slitherOk, setSlitherOk] = useState<boolean | null>(null);
  const [mythrilOk, setMythrilOk] = useState<boolean | null>(null);
  const [highlightLine, setHighlightLine] = useState<number | null>(null);

  useEffect(() => {
    getHealth()
      .then((h) => {
        setSlitherOk(h.slither_available);
        setMythrilOk(h.mythril_available);
      })
      .catch(() => {
        setSlitherOk(false);
        setMythrilOk(false);
      });
  }, []);

  async function runAudit() {
    setLoading(true);
    setError(null);
    setReport(null);
    setHoneypotReport(null);
    try {
      const opts = {
        use_slither: useSlither,
        use_mythril: useMythril,
        use_mempool: useMempool,
        use_honeypot: useHoneypot,
        use_ai: useAi,
        persist,
      };
      let result: AuditReport;
      let usedSource = source;
      if (tab === "source") {
        result = await auditSource({ source, ...opts });
      } else {
        result = await auditAddress({ address, chain, ...opts });
        usedSource = "";
      }
      setReport(result);
      // Run dedicated honeypot scoring if enabled, in parallel-ish
      if (useHoneypot && tab === "source") {
        try {
          const hp = await honeypotSource(usedSource);
          setHoneypotReport(hp);
        } catch {
          /* non-fatal */
        }
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function downloadReport(format: "markdown" | "json" | "pdf") {
    if (!report) return;
    const content = await exportReport(report, format);
    let blob: Blob;
    let ext: string;
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

  return (
    <main className="p-6 max-w-[1600px] mx-auto">
      <header className="mb-6">
        <h1 className="text-xl font-bold tracking-tight">Audit</h1>
        <p className="text-xs text-gray-400">
          Paste source or fetch by address, then run static + symbolic analysis.
        </p>
        <div className="flex items-center gap-2 mt-2 text-[11px]">
          <Pill ok={slitherOk}>Slither: {slitherOk === null ? "…" : slitherOk ? "ready" : "off"}</Pill>
          <Pill ok={mythrilOk}>Mythril: {mythrilOk === null ? "…" : mythrilOk ? "ready" : "off"}</Pill>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="space-y-3">
          <div className="flex gap-2">
            <TabBtn active={tab === "source"} onClick={() => setTab("source")}>
              Source Code
            </TabBtn>
            <TabBtn active={tab === "address"} onClick={() => setTab("address")}>
              Contract Address
            </TabBtn>
          </div>

          {tab === "source" ? (
            <CodeEditor
              value={source}
              onChange={setSource}
              highlightLine={highlightLine}
            />
          ) : (
            <Card className="p-4 space-y-3">
              <Field label="Contract Address">
                <input
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="0x..."
                  className="mt-1 w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm font-mono"
                />
              </Field>
              <Field label="Chain">
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
              </Field>
              <p className="text-xs text-gray-500">
                Source will be fetched from the corresponding block explorer.
              </p>
            </Card>
          )}

          <Card className="p-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <Toggle checked={useSlither} disabled={!slitherOk} onChange={setUseSlither}>
              Slither (static)
            </Toggle>
            <Toggle checked={useMempool} onChange={setUseMempool}>
              Mempool / MEV
            </Toggle>
            <Toggle checked={useHoneypot} onChange={setUseHoneypot}>
              <Flame className="w-3 h-3" /> Honeypot scan
            </Toggle>
            <Toggle checked={useMythril} disabled={!mythrilOk} onChange={setUseMythril}>
              Mythril (symbolic)
            </Toggle>
            <Toggle checked={useAi} onChange={setUseAi}>
              <Wand2 className="w-3 h-3" /> AI explanations
            </Toggle>
            <Toggle checked={persist} onChange={setPersist}>
              <Save className="w-3 h-3" /> Save to history
            </Toggle>
            <div className="col-span-2 flex justify-end mt-2">
              <Button onClick={runAudit} disabled={loading}>
                <Play className="w-4 h-4" />
                {loading ? "Auditing…" : "Run Audit"}
              </Button>
            </div>
          </Card>

          {error && (
            <Card className="p-3 border-red-500/40 text-red-300 text-sm">
              {error}
            </Card>
          )}

          {honeypotReport && <HoneypotPanel report={honeypotReport} />}
        </section>

        <section className="space-y-3">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold">Findings</h2>
            {report && (
              <div className="flex gap-2">
                <Button variant="ghost" onClick={() => downloadReport("markdown")}>
                  <Download className="w-4 h-4" /> .md
                </Button>
                <Button variant="ghost" onClick={() => downloadReport("json")}>
                  <Download className="w-4 h-4" /> .json
                </Button>
                <Button variant="ghost" onClick={() => downloadReport("pdf")}>
                  <Download className="w-4 h-4" /> .pdf
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

function Pill({ ok, children }: { ok: boolean | null; children: React.ReactNode }) {
  return (
    <span
      className={`px-2 py-0.5 rounded ${
        ok === null
          ? "bg-gray-700 text-gray-300"
          : ok
          ? "bg-green-500/20 text-green-300"
          : "bg-yellow-500/20 text-yellow-300"
      }`}
    >
      {children}
    </span>
  );
}

function TabBtn({
  active, onClick, children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      className={`px-3 py-1.5 rounded text-sm ${
        active
          ? "bg-indigo-600 text-white"
          : "bg-gray-800 text-gray-300 hover:bg-gray-700"
      }`}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block text-sm text-gray-300">
      {label}
      {children}
    </label>
  );
}

function Toggle({
  checked, onChange, disabled, children,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className={`flex items-center gap-2 ${disabled ? "opacity-50" : ""}`}>
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      {children}
    </label>
  );
}
