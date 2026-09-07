"use client";

import { ReactNode } from "react";
import { Header } from "./Header";
import { Nav } from "./Nav";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="lux-page-bg min-h-screen">
      <Header />

      {/* Sub-nav bar */}
      <div className="sticky top-16 z-30 border-b border-border bg-card/80 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-6 py-2">
          <Nav />
        </div>
      </div>

      <main className="mx-auto max-w-7xl px-6 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="mt-12 border-t border-border bg-card/60 py-5">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-6">
          <div className="flex items-center gap-2">
            <span className="font-serif text-xs italic text-muted-fg">
              KAQG Pipeline
            </span>
            <span className="text-xs text-muted-fg">·</span>
            <span className="font-mono text-[11px] text-muted-fg">
              Neo4j · OpenRouter · Rust Engine
            </span>
          </div>
          <span className="font-mono text-[11px] text-muted-fg">
            © 2026 KAQG
          </span>
        </div>
      </footer>
    </div>
  );
}
