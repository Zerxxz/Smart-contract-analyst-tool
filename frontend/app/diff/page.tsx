"use client";
import { useState } from "react";
import { CodeEditor } from "@/components/CodeEditor";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DiffViewer } from "@/components/DiffViewer";
import { FindingsPanel } from "@/components/FindingsPanel";
import { SeverityBadge } from "@/components/SeverityBadge";
import { diffAudit } from "@/lib/api";
import type { DiffResult } from "@/lib/types";
import { GitCompareArrows, Plus, Minus } from "lucide-react";

const SAMPLE_OLD = `pragma solidity ^0.8.0;
contract Vault {
    mapping(address => uint256) public balances;
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount);
        (bool ok,) = msg.sender.call{value: amount}("");
        balances[msg.sender] -= amount;
    }
}`;

const SAMPLE_NEW = `pragma solidity 0.8.24;
contract Vault {
    mapping(address => uint256) public balances;
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount);
        balances[msg.sender] -= amount;
        (bool ok,) = msg.sender.call{value: amount}("");
        require(ok);
    }
}`;

export default function DiffPage() {
  const [oldSrc, setOldSrc] = useState(SAMPLE_OLD);
  const [newSrc, setNewSrc] = useState(SAMPLE_NEW);
  const [result, setResult] = useState<DiffResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const r = await diffAudit({ source_old: oldSrc, source_new: newSrc });
      setResult(r);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="p-6 max-w-[1600px] mx-auto">
      <header className="mb-6 flex items-center gap-3">
        <GitCompareArrows className="w-6 h-6 text-indigo-400" />
        <div>
          <h1 className="text-xl font-bold tracking-tight">Diff Audit</h1>
          <p className="text-xs text-gray-400">
            Compare two versions of a contract. See which findings were
            introduced and which were fixed.
          </p>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-gray-300">Old (before)</h3>
          <CodeEditor value={oldSrc} onChange={setOldSrc} />
        </div>
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-gray-300">New (after)</h3>
          <CodeEditor value={newSrc} onChange={setNewSrc} />
        </div>
      </div>

      <div className="flex justify-end mb-4">
        <Button onClick={run} disabled={loading}>
          <GitCompareArrows className="w-4 h-4" />
          {loading ? "Comparing…" : "Run Diff Audit"}
        </Button>
      </div>

      {error && (
        <Card className="p-3 border-red-500/40 text-red-300 text-sm mb-4">
          {error}
        </Card>
      )}

      {result && (
        <div className="space-y-6">
          <Card className="p-4">
            <div className="flex flex-wrap gap-3 items-center text-sm">
              <span className="flex items-center gap-1 text-green-300">
                <Plus className="w-4 h-4" /> {result.lines_added} lines
              </span>
              <span className="flex items-center gap-1 text-red-300">
                <Minus className="w-4 h-4" /> {result.lines_removed} lines
              </span>
              <span className="text-gray-400">|</span>
              <span className="text-green-300">
                +{result.delta.added.length} new findings
              </span>
              <span className="text-red-300">
                -{result.delta.removed.length} fixed findings
              </span>
              <span className="text-gray-400">
                {result.delta.unchanged_count} unchanged
              </span>
            </div>
          </Card>

          <section>
            <h3 className="text-base font-semibold mb-2">Source Diff</h3>
            <DiffViewer diff={result.unified_diff} />
          </section>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <section>
              <h3 className="text-base font-semibold mb-2 text-green-300">
                + New Findings ({result.delta.added.length})
              </h3>
              {result.delta.added.length === 0 ? (
                <Card className="p-4 text-sm text-gray-400">
                  No new findings introduced.
                </Card>
              ) : (
                <div className="space-y-2">
                  {result.delta.added.map((f) => (
                    <Card key={f.id} className="p-3 space-y-1">
                      <div className="flex items-start gap-2">
                        <SeverityBadge severity={f.severity} />
                        <span className="font-semibold text-sm flex-1">
                          {f.title}
                        </span>
                        <span className="text-xs font-mono text-gray-500">
                          {f.detector}
                        </span>
                      </div>
                      <p className="text-xs text-gray-400">{f.description}</p>
                    </Card>
                  ))}
                </div>
              )}
            </section>

            <section>
              <h3 className="text-base font-semibold mb-2 text-red-300">
                - Fixed Findings ({result.delta.removed.length})
              </h3>
              {result.delta.removed.length === 0 ? (
                <Card className="p-4 text-sm text-gray-400">
                  No findings were fixed.
                </Card>
              ) : (
                <div className="space-y-2">
                  {result.delta.removed.map((f) => (
                    <Card
                      key={f.id}
                      className="p-3 space-y-1 border-red-500/30 line-through opacity-70"
                    >
                      <div className="flex items-start gap-2">
                        <SeverityBadge severity={f.severity} />
                        <span className="font-semibold text-sm flex-1">
                          {f.title}
                        </span>
                        <span className="text-xs font-mono text-gray-500">
                          {f.detector}
                        </span>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </section>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <section>
              <h3 className="text-base font-semibold mb-2">Old Report</h3>
              <FindingsPanel report={result.old_report} />
            </section>
            <section>
              <h3 className="text-base font-semibold mb-2">New Report</h3>
              <FindingsPanel report={result.new_report} />
            </section>
          </div>
        </div>
      )}
    </main>
  );
}
