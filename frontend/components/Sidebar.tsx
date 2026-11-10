"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Upload,
  Search,
  AlertTriangle,
  BarChart2,
  Mic,
} from "lucide-react";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/upload", label: "Upload", icon: Upload },
  { href: "/jobs", label: "Jobs", icon: BarChart2 },
  { href: "/search", label: "Search", icon: Search },
  { href: "/reports", label: "Reports", icon: AlertTriangle },
  { href: "/stream", label: "Stream", icon: Mic },
];

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex flex-col w-[220px] min-h-screen bg-[var(--color-surface)] border-r border-[rgba(255,255,255,0.08)] py-6 px-4 fixed left-0 top-0 bottom-0 z-50">
      <div className="flex items-center gap-2.5 mb-8 px-2">
        <img src="/Brain.svg" alt="Synovo" className="w-8 h-8 mr-1" />
        <span className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-br from-[var(--color-primary-light)] to-[var(--color-accent)] tracking-wider">
          Synovo
        </span>
      </div>
      <nav className="flex flex-col gap-1 flex-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active =
            pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 py-2.5 px-3 rounded-md text-sm font-medium transition-colors ${active ? "bg-[rgba(99,102,241,0.15)] text-[var(--color-primary-light)]" : "text-[var(--color-subtle)] hover:bg-[rgba(99,102,241,0.08)] hover:text-[var(--color-content)]"}`}
            >
              <Icon size={18} />
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="pt-4 border-t border-[rgba(255,255,255,0.08)] mt-auto">
        <span className="text-xs text-[var(--color-subtle)] px-2">v0.1.0</span>
      </div>
    </aside>
  );
}
