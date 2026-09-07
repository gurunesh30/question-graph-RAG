"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { StatusBadge } from "@/components/StatusBadge";
import {
  Upload, Brain, Network, FileText, Loader2,
  CheckCircle2, Circle, ArrowRight, Cpu, Database,
  Layers, Zap, BookOpen, Clock, TrendingUp, Info,
} from "lucide-react";

// ── Stat card ────────────────────────────────────────────────────────────────
function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  color = "text-primary",
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  sub?: string;
  color?: string;
}) {
  return (
    <div className="lux-card flex items-start gap-3 p-4">
      <div className={`mt-0.5 rounded-lg bg-muted p-2 ${color}`}>
        <Icon className="h-4 w-4" />
      </div>
      <div>
        <p className="font-mono text-[11px] uppercase tracking-widest text-muted-fg">{label}</p>
        <p className="mt-0.5 text-xl font-semibold text-foreground">{value}</p>
        {sub && <p className="mt-0.5 text-xs text-muted-fg">{sub}</p>}
      </div>
    </div>
  );
}

// ── Pipeline step ─────────────────────────────────────────────────────────────
function PipelineStep({
  n, label, desc, done,
}: { n: number; label: string; desc: string; done?: boolean }) {
  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <div
          className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border-2 text-xs font-bold ${
            done
              ? "border-primary bg-primary text-primary-fg"
              : "border-border bg-card text-muted-fg"
          }`}
        >
          {done ? <CheckCircle2 className="h-3.5 w-3.5" /> : n}
        </div>
        {n < 5 && <div className="mt-1 h-6 w-px bg-border" />}
      </div>
      <div className="pb-4">
        <p className={`text-sm font-semibold ${done ? "text-primary" : "text-foreground"}`}>
          {label}
        </p>
        <p className="text-xs text-muted-fg">{desc}</p>
      </div>
    </div>
  );
}

// ── Tip card ──────────────────────────────────────────────────────────────────
function TipCard({ text }: { text: string }) {
  return (
    <div className="flex gap-2 rounded-lg border border-border bg-accent/30 px-3 py-2.5">
      <Info className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-accent-fg" />
      <p className="text-xs text-accent-fg">{text}</p>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const [file, setFile]       = useState<File | null>(null);
  const [model, setModel]     = useState("openai/gpt-4o-mini");
  const [ingesting, setIngesting] = useState(false);
  const [logs, setLogs]       = useState<string[]>([]);
  const [error, setError]     = useState<string | null>(null);
  const [result, setResult]   = useState<any>(null);

  async function runIngest() {
    if (!file) return;
    setIngesting(true);
    setError(null);
    setResult(null);
    setLogs((l) => [...l, `↑  Uploading ${file.name}…`]);
    try {
      const res  = await api.ingestPdf(file, model);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Ingestion failed");
      setLogs((l) => [...l, `✦  Extracted ${data.char_count} chars from PDF`]);
      setLogs((l) => [...l, `✦  LLM produced ${data.triple_count} triples`]);
      setLogs((l) => [...l, `✓  Graph written to Neo4j`]);
      setResult(data);
    } catch (e: any) {
      setError(e.message);
      setLogs((l) => [...l, `✕  ${e.message}`]);
    } finally {
      setIngesting(false);
    }
  }

  return (
    <AppShell>
      {/* Page heading */}
      <div className="mb-6">
        <h2 className="font-serif text-2xl font-bold text-foreground">Dashboard</h2>
        <p className="mt-1 text-sm text-muted-fg">
          Upload a syllabus PDF to seed the knowledge graph, then generate calibrated MCQs.
        </p>
        <div className="lux-rule mt-3" />
      </div>

      {/* Stats bar */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard icon={Layers}    label="Graph Nodes"  value="—"   sub="run ingest first"  color="text-primary" />
        <StatCard icon={TrendingUp} label="Concepts"    value="—"   sub="difficulty scored"  color="text-emerald-600" />
        <StatCard icon={Brain}     label="Questions"    value="—"   sub="across all bands"   color="text-sky-600" />
        <StatCard icon={Zap}       label="Model"        value="GPT-4o" sub="via OpenRouter"  color="text-amber-600" />
      </div>

      {/* Main grid */}
      <div className="grid gap-6 lg:grid-cols-3">

        {/* Upload card */}
        <div className="lg:col-span-2 space-y-4">
          <div className="lux-card p-6">
            <div className="mb-4 flex items-center gap-2">
              <Upload className="h-4 w-4 text-primary" />
              <h3 className="font-semibold text-foreground">Upload Syllabus PDF</h3>
              <span className="ml-auto rounded-full bg-muted px-2 py-0.5 font-mono text-[10px] text-muted-fg">
                Phase 1 – 3
              </span>
            </div>

            {/* Drop zone */}
            <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-border p-8 text-center transition-colors hover:border-primary/50 hover:bg-muted/40">
              <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
                <FileText className="h-6 w-6 text-primary" />
              </div>
              <span className="text-sm font-medium text-foreground">
                {file ? file.name : "Click to choose a syllabus PDF"}
              </span>
              {!file && (
                <span className="mt-1 text-xs text-muted-fg">Supported: .pdf · max 20 MB</span>
              )}
              {file && (
                <span className="mt-1 font-mono text-xs text-muted-fg">
                  {(file.size / 1024).toFixed(1)} KB
                </span>
              )}
              <input
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                disabled={ingesting}
              />
            </label>

            {/* Controls */}
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2">
                <label className="text-sm text-muted-fg">Model</label>
                <input
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="rounded-md border border-input bg-card px-2.5 py-1.5 font-mono text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <button
                onClick={runIngest}
                disabled={!file || ingesting}
                className="ml-auto inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-fg shadow-sm transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {ingesting
                  ? <Loader2 className="h-4 w-4 animate-spin" />
                  : <Upload className="h-4 w-4" />}
                {ingesting ? "Ingesting…" : "Ingest PDF"}
              </button>
            </div>

            {error && (
              <div className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                {error}
              </div>
            )}
            {result && (
              <div className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
                ✓ Ingest complete — {result.triple_count} triples · {result.char_count} chars
              </div>
            )}
          </div>

          {/* Quick actions */}
          <div className="lux-card p-5">
            <h3 className="mb-3 text-sm font-semibold text-foreground">Quick Actions</h3>
            <div className="grid grid-cols-2 gap-2">
              {[
                { href: "/graph", icon: Network, label: "Explore Knowledge Graph",  sub: "Visualise nodes & edges" },
                { href: "/quiz",  icon: Brain,   label: "Generate MCQs",            sub: "IRT-calibrated questions" },
              ].map(({ href, icon: Icon, label, sub }) => (
                <a
                  key={href}
                  href={href}
                  className="group flex items-center gap-3 rounded-lg border border-border bg-muted/40 p-3 transition-colors hover:border-primary/40 hover:bg-muted"
                >
                  <div className="rounded-md bg-card p-2 shadow-sm group-hover:bg-primary/10">
                    <Icon className="h-4 w-4 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-foreground">{label}</p>
                    <p className="text-xs text-muted-fg">{sub}</p>
                  </div>
                  <ArrowRight className="ml-auto h-3.5 w-3.5 text-muted-fg opacity-0 transition-opacity group-hover:opacity-100" />
                </a>
              ))}
            </div>
          </div>

          {/* Tips */}
          <div className="space-y-2">
            <TipCard text="Ingest runs PDF → LLM triple extraction → Neo4j in one shot. Score difficulty before generating questions." />
            <TipCard text="The IRT difficulty formula maps node degree to [0.1, 1.0]. Higher-degree concepts produce harder questions." />
          </div>
        </div>

        {/* Right column */}
        <div className="flex flex-col gap-4">

          {/* Activity log */}
          <div className="lux-card p-5">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="h-3.5 w-3.5 text-primary" />
                <h3 className="text-sm font-semibold text-foreground">Activity Log</h3>
              </div>
              <StatusBadge label="online" />
            </div>
            <div className="max-h-44 overflow-y-auto space-y-1 font-mono text-xs">
              {logs.length === 0 ? (
                <p className="text-muted-fg">No activity yet.</p>
              ) : (
                logs.map((l, i) => (
                  <div key={i} className="flex gap-2">
                    <span className="text-muted-fg">{String(i + 1).padStart(2, "0")}</span>
                    <span className={l.startsWith("✕") ? "text-destructive" : "text-foreground"}>{l}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Pipeline steps */}
          <div className="lux-card p-5">
            <div className="mb-4 flex items-center gap-2">
              <Cpu className="h-3.5 w-3.5 text-primary" />
              <h3 className="text-sm font-semibold text-foreground">Pipeline Phases</h3>
            </div>
            <div>
              <PipelineStep n={1} label="PDF Extraction"     desc="Rust binary → raw text"          done={!!result} />
              <PipelineStep n={2} label="Triple Extraction"  desc="LLM → head / relation / tail"     done={!!result} />
              <PipelineStep n={3} label="Neo4j Ingestion"    desc="MERGE nodes + relationships"      done={!!result} />
              <PipelineStep n={4} label="IRT Scoring"        desc="Degree → difficulty [0.1, 1.0]"   />
              <PipelineStep n={5} label="MCQ Generation"     desc="Subgraph → distractors → export"  />
            </div>
          </div>

          {/* Tech stack chips */}
          <div className="lux-card p-4">
            <p className="mb-3 font-mono text-[11px] uppercase tracking-widest text-muted-fg">
              Tech Stack
            </p>
            <div className="flex flex-wrap gap-2">
              {[
                { icon: Database, label: "Neo4j Aura" },
                { icon: Cpu,      label: "Rust Engine" },
                { icon: Brain,    label: "OpenRouter"  },
                { icon: BookOpen, label: "KAQG Spec"   },
              ].map(({ icon: Icon, label }) => (
                <div
                  key={label}
                  className="flex items-center gap-1.5 rounded-full border border-border bg-muted px-2.5 py-1 text-xs text-muted-fg"
                >
                  <Icon className="h-3 w-3" />
                  {label}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
