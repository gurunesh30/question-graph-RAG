"use client";

import { Bell, BookOpen, Sparkles, GitBranch } from "lucide-react";
import { StatusBadge } from "./StatusBadge";

export function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-card/90 backdrop-blur-md">
      {/* Top accent rule */}
      <div className="lux-rule" />

      <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-6">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-lg bg-primary shadow-md">
            <BookOpen className="h-5 w-5 text-primary-fg" />
            <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-accent text-[8px] font-bold text-accent-fg">
              KG
            </span>
          </div>
          <div className="leading-tight">
            <div className="flex items-center gap-2">
              <h1 className="font-serif text-base font-bold tracking-wide text-foreground">
                KAQG
              </h1>
              <span className="rounded-full border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-fg">
                v0.2
              </span>
            </div>
            <p className="text-[11px] text-muted-fg tracking-wide">
              Knowledge Augmented Question Generation
            </p>
          </div>
        </div>

        {/* Centre decorative dividers */}
        <div className="mx-4 hidden h-6 w-px bg-border lg:block" />
        <div className="hidden items-center gap-1.5 lg:flex">
          <Sparkles className="h-3.5 w-3.5 text-primary" />
          <span className="font-serif text-xs italic text-muted-fg">
            AI-Powered Syllabus Intelligence
          </span>
        </div>

        {/* Right cluster */}
        <div className="ml-auto flex items-center gap-3">
          {/* Version / branch chip */}
          <div className="hidden items-center gap-1.5 rounded-full border border-border bg-muted px-3 py-1 sm:flex">
            <GitBranch className="h-3 w-3 text-muted-fg" />
            <span className="font-mono text-[11px] text-muted-fg">main</span>
          </div>

          <StatusBadge label="online" />

          <button
            type="button"
            className="relative rounded-lg p-2 text-muted-fg transition-colors hover:bg-muted hover:text-foreground"
            aria-label="Notifications"
          >
            <Bell className="h-4 w-4" />
            {/* Notification dot */}
            <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-primary" />
          </button>
        </div>
      </div>
    </header>
  );
}
