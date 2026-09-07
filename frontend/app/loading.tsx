import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "KAQG — Dashboard",
};

export default function Loading() {
  return (
    <div className="flex h-screen items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
        <p className="text-sm text-slate-500">Loading KAQG…</p>
      </div>
    </div>
  );
}