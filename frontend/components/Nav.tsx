"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Brain, LayoutDashboard, Network } from "lucide-react";

const items = [
  { href: "/",      label: "Dashboard",     icon: LayoutDashboard },
  { href: "/graph", label: "Graph Explorer", icon: Network },
  { href: "/quiz",  label: "Quiz Generator", icon: Brain },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <nav className="flex items-center gap-1">
      {items.map(({ href, label, icon: Icon }) => {
        const active = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            className={`relative flex items-center gap-2 rounded-md px-3.5 py-2 text-sm font-medium transition-all duration-150 ${
              active
                ? "bg-primary text-primary-fg shadow-sm"
                : "text-muted-fg hover:bg-muted hover:text-foreground"
            }`}
          >
            <Icon className="h-4 w-4 flex-shrink-0" />
            <span className="hidden sm:inline">{label}</span>
            {active && (
              <span className="absolute -bottom-[13px] left-1/2 h-0.5 w-4 -translate-x-1/2 rounded-full bg-primary" />
            )}
          </Link>
        );
      })}
    </nav>
  );
}
