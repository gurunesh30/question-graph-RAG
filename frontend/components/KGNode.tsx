import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";

export type NodeKind = "hierarchy" | "concept" | "textual";

const palette: Record<NodeKind, { bg: string; border: string; text: string }> = {
  hierarchy: { bg: "#DCFCE7", border: "#16A34A", text: "#14532D" },
  concept: { bg: "#FCE7F3", border: "#DB2777", text: "#9D174D" },
  textual: { bg: "#FEF3C7", border: "#A16207", text: "#78350F" },
};

export interface GraphNodeData {
  label: string;
  name: string;
  properties?: Record<string, unknown>;
}

export const KGNode = memo(function KGNode({ data, selected }: NodeProps<GraphNodeData>) {
  const kind = (data.label as NodeKind) ?? "concept";
  const p = palette[kind] ?? palette.concept;
  return (
    <div
      className="min-w-[180px] max-w-[240px] rounded-lg border-2 px-3 py-2 shadow-sm"
      style={{ backgroundColor: p.bg, borderColor: p.border, color: p.text }}
    >
      <Handle type="target" position={Position.Left} className="!bg-slate-300" />
      <div className="text-xs font-semibold uppercase tracking-wide opacity-70">{kind}</div>
      <div className="mt-0.5 text-sm font-semibold" title={data.name}>
        {data.name.length > 28 ? data.name.slice(0, 26) + "…" : data.name}
      </div>
      {selected && (
        <div className="mt-1 border-t border-current pt-1 text-xs opacity-80">
          {Object.entries(data.properties ?? {}).map(([k, v]) => (
            <div key={k}>
              <span className="opacity-60">{k}: </span>
              {String(v)}
            </div>
          ))}
        </div>
      )}
      <Handle type="source" position={Position.Right} className="!bg-slate-300" />
    </div>
  );
});

KGNode.displayName = "KGNode";