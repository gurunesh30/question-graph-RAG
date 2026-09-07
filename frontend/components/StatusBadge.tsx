import React from "react";

export interface StatusBadgeProps {
  label: "online" | "offline" | "loading" | "scoring" | "ready";
}

const styles: Record<StatusBadgeProps["label"], { dot: string; pill: string }> = {
  online:  { dot: "bg-emerald-500",   pill: "border-emerald-200 bg-emerald-50  text-emerald-700" },
  offline: { dot: "bg-slate-400",     pill: "border-slate-200  bg-slate-50    text-slate-500"   },
  loading: { dot: "bg-amber-400 animate-pulse", pill: "border-amber-200  bg-amber-50   text-amber-700"  },
  scoring: { dot: "bg-primary animate-pulse",   pill: "border-border    bg-muted      text-muted-fg"   },
  ready:   { dot: "bg-sky-500",       pill: "border-sky-200   bg-sky-50     text-sky-700"    },
};

export function StatusBadge({ label }: StatusBadgeProps) {
  const s = styles[label];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[11px] font-medium ${s.pill}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      {label}
    </span>
  );
}
