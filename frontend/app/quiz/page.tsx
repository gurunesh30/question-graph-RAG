"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import {
  Loader2, Brain, Download, FileJson, FileText,
  CheckCircle2, Circle, Sparkles, BarChart2,
  BookOpen, Lightbulb, Target, TrendingUp, Info,
} from "lucide-react";

type Difficulty = "easy" | "medium" | "hard";

// ── Difficulty meter ──────────────────────────────────────────────────────────
const difficultyMeta: Record<Difficulty, { color: string; fill: string; bars: number; desc: string }> = {
  easy:   { color: "text-emerald-600",  fill: "bg-emerald-500",  bars: 1, desc: "Low node-degree concepts · IRT b ≤ 0.4" },
  medium: { color: "text-amber-600",    fill: "bg-amber-500",    bars: 2, desc: "Mid node-degree concepts · IRT b 0.4–0.7" },
  hard:   { color: "text-red-600",      fill: "bg-red-500",      bars: 3, desc: "High node-degree concepts · IRT b ≥ 0.7" },
};

function DifficultyMeter({ value }: { value: Difficulty }) {
  const m = difficultyMeta[value];
  return (
    <div className="flex items-center gap-1.5">
      {[1, 2, 3].map((b) => (
        <div
          key={b}
          className={`h-3 rounded-sm transition-all ${
            b <= m.bars ? m.fill : "bg-muted"
          }`}
          style={{ width: b * 6 + 6 }}
        />
      ))}
      <span className={`ml-1 text-xs font-semibold capitalize ${m.color}`}>{value}</span>
    </div>
  );
}

// ── Stat chip ─────────────────────────────────────────────────────────────────
function StatChip({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string | number }) {
  return (
    <div className="flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-xs text-foreground">
      <Icon className="h-3 w-3 text-primary" />
      <span className="text-muted-fg">{label}</span>
      <span className="font-mono font-medium">{value}</span>
    </div>
  );
}

// ── Tip row ───────────────────────────────────────────────────────────────────
function Tip({ text }: { text: string }) {
  return (
    <div className="flex gap-2 text-xs">
      <Lightbulb className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-primary" />
      <span className="text-muted-fg">{text}</span>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function QuizPage() {
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");
  const [count, setCount]           = useState(5);
  const [mock, setMock]             = useState(false);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState<string | null>(null);
  const [questions, setQuestions]   = useState<any[]>([]);

  async function generate() {
    setLoading(true);
    setError(null);
    setQuestions([]);
    try {
      const data = await api.generateMcq(difficulty, count, mock) as { questions?: any[] };
      setQuestions(data.questions ?? []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function downloadJson() {
    const blob = new Blob(
      [JSON.stringify({ difficulty, count, questions }, null, 2)],
      { type: "application/json" },
    );
    const url = URL.createObjectURL(blob);
    const a   = document.createElement("a");
    a.href = url; a.download = `${difficulty}.json`; a.click();
    URL.revokeObjectURL(url);
  }

  function downloadMd() {
    const lines: string[] = [
      `# Question Bank — ${difficulty}`,
      `Mode: ${mock ? "mock" : "live"} · ${questions.length} questions`,
      "",
    ];
    questions.forEach((q, i) => {
      lines.push(`## ${i + 1}. ${q.question}`);
      for (const [label, option] of Object.entries(q.options ?? {})) {
        const marker = label === q.correct_answer ? " **(correct)**" : "";
        lines.push(`- **${label}.** ${option}${marker}`);
      }
      lines.push(``, `_Explanation:_ ${q.explanation}`, ``);
    });
    const blob = new Blob([lines.join("\n")], { type: "text/markdown" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href = url; a.download = `${difficulty}.md`; a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <AppShell>
      {/* Page heading */}
      <div className="mb-5">
        <h2 className="font-serif text-2xl font-bold text-foreground">Quiz Generator</h2>
        <p className="mt-1 text-sm text-muted-fg">
          IRT-calibrated multiple-choice questions sampled from the knowledge graph.
        </p>
        <div className="lux-rule mt-2" />
      </div>

      <div className="grid gap-6 lg:grid-cols-4">

        {/* Controls sidebar */}
        <div className="space-y-4 lg:col-span-1">

          {/* Difficulty selector */}
          <div className="lux-card p-4 space-y-3">
            <p className="font-mono text-[11px] uppercase tracking-widest text-muted-fg">Difficulty</p>
            <div className="flex flex-col gap-1.5">
              {(["easy", "medium", "hard"] as Difficulty[]).map((d) => (
                <button
                  key={d}
                  onClick={() => setDifficulty(d)}
                  className={`flex items-center justify-between rounded-md border px-3 py-2 text-sm font-medium transition-all ${
                    difficulty === d
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border bg-card text-muted-fg hover:bg-muted"
                  }`}
                >
                  <span className="capitalize">{d}</span>
                  <DifficultyMeter value={d} />
                </button>
              ))}
            </div>
            <p className="text-[11px] text-muted-fg">{difficultyMeta[difficulty].desc}</p>
          </div>

          {/* Count + mock */}
          <div className="lux-card p-4 space-y-3">
            <div>
              <label className="font-mono text-[11px] uppercase tracking-widest text-muted-fg">
                Question Count
              </label>
              <div className="mt-2 flex items-center gap-2">
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={count}
                  onChange={(e) => setCount(Math.max(1, Math.min(20, Number(e.target.value) || 1)))}
                  className="w-20 rounded-md border border-input bg-card px-2.5 py-1.5 font-mono text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                />
                <span className="text-xs text-muted-fg">/ 20 max</span>
              </div>
            </div>

            <label className="flex cursor-pointer items-center gap-2 text-sm text-foreground">
              <div className={`relative h-5 w-9 rounded-full transition-colors ${mock ? "bg-primary" : "bg-muted"}`}>
                <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${mock ? "translate-x-4" : "translate-x-0.5"}`} />
                <input type="checkbox" checked={mock} onChange={(e) => setMock(e.target.checked)} className="sr-only" />
              </div>
              <span>Mock mode <span className="text-muted-fg text-xs">(no LLM)</span></span>
            </label>
          </div>

          {/* Generate button */}
          <button
            onClick={generate}
            disabled={loading}
            className="w-full inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-primary-fg shadow-sm transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {loading ? "Generating…" : "Generate Questions"}
          </button>

          {/* Download buttons */}
          {questions.length > 0 && (
            <div className="flex gap-2">
              <button
                onClick={downloadJson}
                className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-md border border-border bg-card px-3 py-2 text-xs text-foreground shadow-sm hover:bg-muted"
              >
                <FileJson className="h-3.5 w-3.5" /> JSON
              </button>
              <button
                onClick={downloadMd}
                className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-md border border-border bg-card px-3 py-2 text-xs text-foreground shadow-sm hover:bg-muted"
              >
                <FileText className="h-3.5 w-3.5" /> MD
              </button>
            </div>
          )}

          {/* Tips */}
          <div className="lux-card p-4 space-y-2.5">
            <p className="font-mono text-[11px] uppercase tracking-widest text-muted-fg">Tips</p>
            <Tip text="Run --score first so difficulty values are populated in Neo4j." />
            <Tip text="Mock mode returns placeholder questions without calling the LLM." />
            <Tip text="Hard questions target high-centrality concepts with many IS_A edges." />
          </div>
        </div>

        {/* Question list */}
        <div className="lg:col-span-3">

          {/* Stats row */}
          {questions.length > 0 && (
            <div className="mb-4 flex flex-wrap gap-2">
              <StatChip icon={Brain}     label="Generated"  value={questions.length} />
              <StatChip icon={Target}    label="Difficulty" value={difficulty} />
              <StatChip icon={BarChart2} label="Mode"       value={mock ? "mock" : "live"} />
              <StatChip icon={TrendingUp} label="IRT band"  value={difficultyMeta[difficulty].desc.split("·")[1]?.trim() ?? "—"} />
            </div>
          )}

          {error && (
            <div className="mb-4 rounded-md border border-destructive/30 bg-destructive/10 px-4 py-2.5 text-sm text-destructive">
              {error}
            </div>
          )}

          {loading ? (
            <div className="flex h-64 flex-col items-center justify-center gap-3">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="font-mono text-xs text-muted-fg">Sampling subgraph · calling LLM…</p>
            </div>
          ) : questions.length === 0 ? (
            <div className="flex h-64 flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border">
              <Brain className="h-10 w-10 text-muted-fg/30" />
              <div className="text-center">
                <p className="text-sm font-medium text-foreground">No questions yet</p>
                <p className="mt-0.5 text-xs text-muted-fg">
                  Choose a difficulty and click Generate Questions.
                </p>
              </div>
              <div className="flex items-center gap-2 rounded-full border border-border bg-muted px-3 py-1.5">
                <Info className="h-3 w-3 text-muted-fg" />
                <span className="text-xs text-muted-fg">Ensure the API server is running on :8001</span>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {questions.map((q, i) => (
                <div key={i} className="lux-card p-5">
                  {/* Question header */}
                  <div className="mb-3 flex flex-wrap items-center gap-2">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary font-mono text-xs font-bold text-primary-fg">
                      {i + 1}
                    </span>
                    <span className="rounded-full border border-border bg-muted px-2 py-0.5 font-mono text-[10px] capitalize text-muted-fg">
                      {q.difficulty ?? difficulty}
                    </span>
                    {q.concept && (
                      <span className="flex items-center gap-1 rounded-full border border-border bg-muted px-2 py-0.5 text-[10px] text-muted-fg">
                        <BookOpen className="h-2.5 w-2.5" />
                        {q.concept}
                      </span>
                    )}
                  </div>

                  <h3 className="text-sm font-semibold text-foreground leading-snug">{q.question}</h3>

                  {/* Options */}
                  <ul className="mt-3 space-y-1.5">
                    {Object.entries(q.options ?? {}).map(([label, option]) => {
                      const isCorrect = label === q.correct_answer;
                      return (
                        <li
                          key={label}
                          className={`flex items-center gap-2.5 rounded-lg border px-3 py-2 text-sm transition-colors ${
                            isCorrect
                              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                              : "border-border bg-muted/30 text-foreground"
                          }`}
                        >
                          {isCorrect
                            ? <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-emerald-600" />
                            : <Circle       className="h-4 w-4 flex-shrink-0 text-muted-fg/50" />}
                          <span className="font-medium">{label}.</span>
                          <span>{String(option)}</span>
                        </li>
                      );
                    })}
                  </ul>

                  {/* Explanation */}
                  <details className="mt-3">
                    <summary className="cursor-pointer text-xs font-medium text-primary hover:opacity-80">
                      Show explanation
                    </summary>
                    <p className="mt-2 rounded-md bg-accent/30 px-3 py-2 text-xs text-accent-fg leading-relaxed">
                      {q.explanation}
                    </p>
                  </details>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
