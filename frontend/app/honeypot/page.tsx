"use client";
import { useState } from "react";
import { CodeEditor } from "@/components/CodeEditor";
import { HoneypotPanel } from "@/components/HoneypotPanel";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { honeypotSource } from "@/lib/api";
import type { HoneypotReport } from "@/lib/types";
import { Flame, Play } from "lucide-react";

const SAMPLE = `pragma solidity ^0.8.0;
contract SuspiciousToken {
    address public owner;
    mapping(address => uint256) balances;
    mapping(address => bool) public blacklist;
    uint256 public sellTax = 99;

    function _transfer(address from, address to, uint256 amount) internal {
        require(!blacklist[from], "blacklisted");
        if (msg.sender != owner) {
            // only owner can sell freely
            require(false, "trading paused");
        }
        balances[from] -= amount;
        balances[to] += amount;
    }

    function setSellTax(uint256 newTax) external {
        sellTax = newTax;
    }

    function mint(address to, uint256 amount) external {
        balances[to] += amount;
    }
}
`;

export default function HoneypotPage() {
  const [source, setSource] = useState(SAMPLE);
  const [report, setReport] = useState<HoneypotReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      setReport(await honeypotSource(source));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="p-6 max-w-[1600px] mx-auto">
      <header className="mb-6 flex items-center gap-3">
        <Flame className="w-6 h-6 text-orange-400" />
        <div>
          <h1 className="text-xl font-bold tracking-tight">Honeypot Scanner</h1>
          <p className="text-xs text-gray-400">
            Risk-score a token contract for common rug-pull and honeypot patterns.
          </p>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="space-y-3">
          <CodeEditor value={source} onChange={setSource} />
          <div className="flex justify-end">
            <Button onClick={run} disabled={loading}>
              <Play className="w-4 h-4" />
              {loading ? "Scanning…" : "Scan for Honeypot"}
            </Button>
          </div>
          {error && (
            <Card className="p-3 border-red-500/40 text-red-300 text-sm">
              {error}
            </Card>
          )}
        </section>
        <section>
          {report ? (
            <HoneypotPanel report={report} />
          ) : (
            <Card className="p-6 text-gray-400 text-sm">
              Run a scan to see risk score and indicators here.
            </Card>
          )}
        </section>
      </div>
    </main>
  );
}
