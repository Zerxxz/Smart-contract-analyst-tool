"use client";
import { useMemo } from "react";
import dynamic from "next/dynamic";
import type { CallGraph, GraphEdge } from "@/lib/types";
import "reactflow/dist/style.css";

const ReactFlow = dynamic(
  () => import("reactflow").then((m) => m.default),
  { ssr: false, loading: () => <FlowLoading /> }
);
const Background = dynamic(
  () => import("reactflow").then((m) => m.Background),
  { ssr: false }
);
const Controls = dynamic(
  () => import("reactflow").then((m) => m.Controls),
  { ssr: false }
);
const MiniMap = dynamic(
  () => import("reactflow").then((m) => m.MiniMap),
  { ssr: false }
);

function FlowLoading() {
  return (
    <div className="h-full flex items-center justify-center text-gray-400 text-sm">
      Loading graph…
    </div>
  );
}

const VISIBILITY_COLOR: Record<string, string> = {
  public: "#3b82f6",
  external: "#10b981",
  internal: "#9ca3af",
  private: "#6b7280",
};

function layoutGraph(graph: CallGraph) {
  // Group nodes per contract; lay out contracts horizontally and
  // their member functions vertically.
  const byContract = new Map<string, typeof graph.nodes>();
  for (const n of graph.nodes) {
    if (!byContract.has(n.contract)) byContract.set(n.contract, []);
    byContract.get(n.contract)!.push(n);
  }

  const nodes: any[] = [];
  const COL_W = 280;
  const ROW_H = 60;
  const HEADER = 40;

  let col = 0;
  for (const [contract, fns] of byContract.entries()) {
    nodes.push({
      id: `__group_${contract}`,
      type: "group",
      data: { label: contract },
      position: { x: col * COL_W, y: 0 },
      style: {
        width: COL_W - 30,
        height: HEADER + fns.length * ROW_H + 20,
        backgroundColor: "rgba(99, 102, 241, 0.08)",
        border: "1px solid rgba(99, 102, 241, 0.4)",
        borderRadius: 8,
      },
    });
    nodes.push({
      id: `__group_${contract}_label`,
      data: { label: contract },
      position: { x: col * COL_W + 12, y: 8 },
      draggable: false,
      selectable: false,
      style: {
        background: "transparent",
        border: "none",
        color: "#a5b4fc",
        fontSize: 12,
        fontWeight: 600,
        padding: 0,
      },
    });
    fns.forEach((fn, idx) => {
      nodes.push({
        id: fn.id,
        data: {
          label: (
            <div className="text-xs text-left">
              <div
                className="font-semibold truncate"
                style={{ color: VISIBILITY_COLOR[fn.visibility] || "#fff" }}
              >
                {fn.is_constructor ? "constructor" : fn.label}
                {fn.has_modifier && (
                  <span className="ml-1 text-[10px] text-orange-300">●</span>
                )}
              </div>
              <div className="text-[10px] text-gray-400">{fn.visibility}</div>
            </div>
          ),
        },
        position: { x: col * COL_W + 16, y: HEADER + idx * ROW_H },
        style: {
          width: COL_W - 60,
          background: "#1f2937",
          border: `1px solid ${VISIBILITY_COLOR[fn.visibility] || "#374151"}`,
          borderRadius: 6,
          padding: 6,
          color: "#e5e7eb",
        },
      });
    });
    col++;
  }

  const edges = graph.edges
    .filter(
      (e) =>
        graph.nodes.some((n) => n.id === e.source) &&
        graph.nodes.some((n) => n.id === e.target)
    )
    .map((e: GraphEdge, i: number) => ({
      id: `e${i}`,
      source: e.source,
      target: e.target,
      animated: e.type === "call",
      label: e.type === "modifier" ? "modifier" : undefined,
      style: {
        stroke:
          e.type === "inheritance"
            ? "#a78bfa"
            : e.type === "modifier"
            ? "#f59e0b"
            : "#60a5fa",
        strokeWidth: e.type === "inheritance" ? 2 : 1.5,
      },
    }));

  return { nodes, edges };
}

export function CallGraphViewer({ graph }: { graph: CallGraph | null }) {
  const { nodes, edges } = useMemo(
    () => (graph ? layoutGraph(graph) : { nodes: [], edges: [] }),
    [graph]
  );

  if (!graph) {
    return (
      <div className="h-[60vh] flex items-center justify-center text-gray-400 text-sm border border-[var(--border)] rounded-lg">
        Build a graph to see contract structure here.
      </div>
    );
  }
  if (graph.nodes.length === 0) {
    return (
      <div className="h-[60vh] flex items-center justify-center text-gray-400 text-sm border border-[var(--border)] rounded-lg">
        No contracts or functions detected in source.
      </div>
    );
  }

  return (
    <div className="h-[70vh] border border-[var(--border)] rounded-lg overflow-hidden bg-[var(--panel)]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={16} color="#374151" />
        <Controls className="!bg-gray-900 !border-gray-700" />
        <MiniMap
          pannable
          zoomable
          style={{ background: "#0f172a" }}
          maskColor="rgba(15,23,42,0.7)"
          nodeColor="#6366f1"
        />
      </ReactFlow>
    </div>
  );
}
