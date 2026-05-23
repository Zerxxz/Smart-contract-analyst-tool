"use client";
import { useState } from "react";
import { CodeEditor } from "@/components/CodeEditor";
import { CallGraphViewer } from "@/components/CallGraphViewer";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { buildGraph } from "@/lib/api";
import type { CallGraph } from "@/lib/types";
import { Network, Play } from "lucide-react";

const SAMPLE = `pragma solidity ^0.8.0;

contract Ownable {
    address public owner;
    modifier onlyOwner() { require(msg.sender == owner, "auth"); _; }
    function transferOwnership(address newOwner) external onlyOwner {
        owner = newOwner;
    }
}

contract Token is Ownable {
    mapping(address => uint256) balances;

    function mint(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
    }

    function _mint(address to, uint256 amount) internal {
        balances[to] += amount;
    }

    function transfer(address to, uint256 amount) external {
        balances[msg.sender] -= amount;
        balances[to] += amount;
    }
}
`;

export default function GraphPage() {
  const [source, setSource] = useState(SAMPLE);
  const [graph, setGraph] = useState<CallGraph | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const g = await buildGraph(source);
      setGraph(g);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="p-6 max-w-[1600px] mx-auto">
      <header className="mb-6 flex items-center gap-3">
        <Network className="w-6 h-6 text-indigo-400" />
        <div>
          <h1 className="text-xl font-bold tracking-tight">Call Graph</h1>
          <p className="text-xs text-gray-400">
            Visualize contract structure: functions, inheritance, and call edges.
          </p>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="space-y-3">
          <CodeEditor value={source} onChange={setSource} />
          <div className="flex justify-end">
            <Button onClick={run} disabled={loading}>
              <Play className="w-4 h-4" />
              {loading ? "Building…" : "Build Graph"}
            </Button>
          </div>
          {error && (
            <Card className="p-3 border-red-500/40 text-red-300 text-sm">
              {error}
            </Card>
          )}
          {graph && (
            <Card className="p-3 text-xs text-gray-400 space-y-1">
              <div>
                <span className="text-gray-300 font-semibold">
                  {graph.contracts.length}
                </span>{" "}
                contracts:{" "}
                <span className="font-mono text-indigo-300">
                  {graph.contracts.join(", ")}
                </span>
              </div>
              <div>
                <span className="text-gray-300 font-semibold">
                  {graph.nodes.length}
                </span>{" "}
                functions/modifiers,{" "}
                <span className="text-gray-300 font-semibold">
                  {graph.edges.length}
                </span>{" "}
                edges
              </div>
              <div className="flex gap-3 pt-2 text-[10px] uppercase">
                <Legend color="#60a5fa" label="call" />
                <Legend color="#a78bfa" label="inheritance" />
                <Legend color="#f59e0b" label="modifier" />
              </div>
            </Card>
          )}
        </section>
        <section>
          <CallGraphViewer graph={graph} />
        </section>
      </div>
    </main>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1">
      <span
        className="inline-block w-4 h-0.5 rounded"
        style={{ backgroundColor: color }}
      />
      {label}
    </span>
  );
}
