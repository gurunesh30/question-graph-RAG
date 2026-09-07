"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { StatusBadge } from "@/components/StatusBadge";
import {
  Loader2, Network, RefreshCw, Layers, GitBranch,
  Tag, Info, Filter, Search,
} from "lucide-react";

import ReactFlow, {
  Background,
  Controls,
  Edge,
  Node,
  NodeTypes,
  useNodesState,
  useEdgesState,
  addEdge,
  type Connection,
} from "reactflow";
import "reactflow/dist/style.css";

import { KGNode, type GraphNodeData } from "@/components/KGNode";

const nodeTypes: NodeTypes = { kg: KGNode };

// ── Legend chip ───────────────────────────────────────────────────────────────
function LegendChip({
  color, border, label, count,
}: { color: string; border: string; label: string; count?: number }) {
  return (
    <div className="flex items-center gap-2 rounded-md border px-3 py-1.5 text-xs"
         style={{ borderColor: border, background: color }}>
      <span className="h-2 w-2 rounded-full" style={{ background: border }} />
      <span className="font-medium capitalize" style={{ color: border }}>{label}</span>
      {count !== undefined && (
        <span className="ml-auto font-mono text-[10px] opacity-70">{count}</span>
      )}
    </div>
  );
}

// ── Stat chip ─────────────────────────────────────────────────────────────────
function StatChip({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string | number }) {
  return (
    <div className="flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs text-foreground">
      <Icon className="h-3 w-3 text-primary" />
      <span className="text-muted-fg">{label}</span>
      <span className="font-mono font-medium">{value}</span>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function GraphExplorerPage() {
  const [nodes, setNodes, onNodesChange] = useNodesState<GraphNodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedNode, setSelectedNode] = useState<Node<GraphNodeData> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data: any = await api.graphData();
      const flowNodes: Node<GraphNodeData>[] = data.nodes.map((n: any, i: number) => ({
        id: n.id,
        type: "kg",
        position: { x: (i % 6) * 220, y: Math.floor(i / 6) * 140 },
        data: { label: n.label, name: n.name, properties: n.properties },
      }));
      const flowEdges: Edge[] = data.edges.map((e: any) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        type: "smoothstep",
        animated: true,
      }));
      setNodes(flowNodes);
      setEdges(flowEdges);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const hierarchyCount = nodes.filter(n => n.data.label === "hierarchy").length;
  const conceptCount   = nodes.filter(n => n.data.label === "concept").length;
  const textualCount   = nodes.filter(n => n.data.label === "textual").length;

  return (
    <AppShell>
      {/* Header row */}
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="font-serif text-2xl font-bold text-foreground">Knowledge Graph Explorer</h2>
          <p className="mt-1 text-sm text-muted-fg">
            Interactive three-tier visualisation — hierarchy · concept · textual
          </p>
          <div className="lux-rule mt-2" />
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge label={loading ? "loading" : "online"} />
          <button
            onClick={load}
            className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-3 py-2 text-sm text-foreground shadow-sm transition hover:bg-muted"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats bar */}
      <div className="mb-4 flex flex-wrap gap-2">
        <StatChip icon={Layers}    label="Nodes"  value={nodes.length || "—"} />
        <StatChip icon={GitBranch} label="Edges"  value={edges.length || "—"} />
        <StatChip icon={Network}   label="Hierarchy" value={hierarchyCount || "—"} />
        <StatChip icon={Tag}       label="Concepts"  value={conceptCount   || "—"} />
        <StatChip icon={Filter}    label="Textual"   value={textualCount   || "—"} />
      </div>

      <div className="flex gap-5">
        {/* Canvas */}
        <div className="flex-1 overflow-hidden rounded-xl border border-border bg-card shadow-md">
          {/* Legend bar */}
          <div className="flex flex-wrap items-center gap-2 border-b border-border px-4 py-2.5">
            <span className="mr-1 font-mono text-[10px] uppercase tracking-widest text-muted-fg">Legend</span>
            <LegendChip color="#DCFCE7" border="#16A34A" label="Hierarchy" count={hierarchyCount} />
            <LegendChip color="#FCE7F3" border="#DB2777" label="Concept"   count={conceptCount}   />
            <LegendChip color="#FEF3C7" border="#A16207" label="Textual"   count={textualCount}   />

            {/* Placeholder search chip */}
            <div className="ml-auto flex items-center gap-1.5 rounded-full border border-border bg-muted px-3 py-1 text-xs text-muted-fg">
              <Search className="h-3 w-3" />
              <span>Search nodes…</span>
            </div>
          </div>

          <div className="h-[560px]">
            {loading ? (
              <div className="flex h-full flex-col items-center justify-center gap-3">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p className="font-mono text-xs text-muted-fg">Fetching graph from Neo4j…</p>
              </div>
            ) : error ? (
              <div className="flex h-full flex-col items-center justify-center gap-2 p-8 text-center">
                <Network className="h-10 w-10 text-muted-fg/40" />
                <p className="text-sm font-medium text-destructive">{error}</p>
                <p className="text-xs text-muted-fg">Make sure the API server is running on port 8001.</p>
              </div>
            ) : nodes.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center gap-2 p-8 text-center">
                <Layers className="h-10 w-10 text-muted-fg/30" />
                <p className="text-sm font-medium text-foreground">Graph is empty</p>
                <p className="text-xs text-muted-fg">Ingest a syllabus PDF from the Dashboard first.</p>
              </div>
            ) : (
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={(params: Connection) => setEdges((eds) => addEdge(params, eds))}
                onNodeClick={(_, node) => setSelectedNode(node as Node<GraphNodeData>)}
                nodeTypes={nodeTypes}
                fitView
              >
                <Background color="var(--border)" gap={20} />
                <Controls />
              </ReactFlow>
            )}
          </div>
        </div>

        {/* Inspector panel */}
        <div className="w-72 flex-shrink-0 space-y-4">
          <div className="lux-card p-5">
            <div className="mb-3 flex items-center gap-2">
              <Info className="h-3.5 w-3.5 text-primary" />
              <h3 className="text-sm font-semibold text-foreground">Node Inspector</h3>
            </div>
            {selectedNode ? (
              <div className="space-y-3">
                <div className="rounded-md bg-muted px-3 py-1.5">
                  <p className="font-mono text-[10px] uppercase tracking-widest text-muted-fg">
                    {selectedNode.data.label}
                  </p>
                  <p className="mt-0.5 text-sm font-semibold text-foreground">
                    {selectedNode.data.name}
                  </p>
                </div>
                <div className="space-y-1.5 text-xs">
                  {Object.entries(selectedNode.data.properties ?? {}).map(([k, v]) => (
                    <div key={k} className="flex items-baseline justify-between gap-2">
                      <span className="text-muted-fg">{k}</span>
                      <span className="rounded bg-muted px-1.5 py-0.5 font-mono font-medium text-foreground">
                        {String(v)}
                      </span>
                    </div>
                  ))}
                  {Object.keys(selectedNode.data.properties ?? {}).length === 0 && (
                    <p className="text-muted-fg">No additional properties.</p>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2 py-6 text-center">
                <Network className="h-8 w-8 text-muted-fg/30" />
                <p className="text-xs text-muted-fg">Click any node to inspect its properties.</p>
              </div>
            )}
          </div>

          {/* Graph info card */}
          <div className="lux-card p-4 space-y-2">
            <p className="font-mono text-[10px] uppercase tracking-widest text-muted-fg">About the Graph</p>
            {[
              ["Tier 1", "Hierarchy", "Units & chapters"],
              ["Tier 2", "Concept",   "Academic topics"],
              ["Tier 3", "Textual",   "Algorithms & terms"],
            ].map(([tier, name, desc]) => (
              <div key={tier} className="flex items-start gap-2 text-xs">
                <span className="mt-0.5 rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-fg">
                  {tier}
                </span>
                <div>
                  <span className="font-medium text-foreground">{name}</span>
                  <span className="ml-1 text-muted-fg">— {desc}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Relationship key */}
          <div className="lux-card p-4 space-y-2">
            <p className="font-mono text-[10px] uppercase tracking-widest text-muted-fg">Relationships</p>
            {[
              ["PART_OF",    "Hierarchy → Hierarchy"],
              ["INCLUDE_IN", "Concept → Hierarchy"],
              ["IS_A",       "Textual → Concept"],
            ].map(([rel, desc]) => (
              <div key={rel} className="text-xs">
                <span className="font-mono font-medium text-primary">{rel}</span>
                <span className="ml-2 text-muted-fg">{desc}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
