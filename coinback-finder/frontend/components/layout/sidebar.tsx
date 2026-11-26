"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";

import { cn } from "@/services/cn";
import { NAV_SECTIONS, isActive } from "./nav";

export function Sidebar({ collapsed, onToggle, mobileOpen, onNavigate }: { collapsed: boolean; onToggle: () => void; mobileOpen: boolean; onNavigate: () => void }) {
  const pathname = usePathname();
  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-40 flex flex-col border-r border-sidebar-line bg-sidebar text-sidebar-fg transition-[width,transform] duration-150",
        collapsed ? "lg:w-14" : "lg:w-56",
        "w-60",
        mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
      )}
    >
      <div className={cn("flex h-12 items-center gap-2.5 border-b border-sidebar-line px-3.5", collapsed && "lg:justify-center lg:px-0")}>
        <svg viewBox="0 0 32 32" className="h-6 w-6 shrink-0" aria-hidden>
          <rect width="32" height="32" rx="6" fill="hsl(var(--sidebar-hover))" />
          <circle cx="16" cy="16" r="8.5" fill="none" stroke="hsl(var(--sidebar-fg))" strokeWidth="2.4" />
          <path d="M19.6 12.6a5 5 0 1 0 0 6.8" fill="none" stroke="hsl(var(--positive))" strokeWidth="2.4" strokeLinecap="round" />
        </svg>
        <div className={cn("min-w-0 leading-tight", collapsed && "lg:hidden")}>
          <p className="truncate text-sm font-semibold tracking-tight">CoinBack Finder</p>
          <p className="truncate text-2xs text-sidebar-muted">Flipkart · INR · IST</p>
        </div>
      </div>

      <nav className="scrollbar-thin flex-1 overflow-y-auto px-2 py-3" aria-label="Primary">
        {NAV_SECTIONS.map((section) => (
          <div key={section.title} className="mb-4">
            <p className={cn("px-2 pb-1.5 text-2xs font-medium text-sidebar-muted", collapsed && "lg:sr-only")}>{section.title}</p>
            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const active = isActive(pathname, item.href);
                const Icon = item.icon;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      onClick={onNavigate}
                      title={collapsed ? item.label : undefined}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "relative flex h-8 items-center gap-2.5 rounded px-2 text-sm transition-colors",
                        active ? "bg-sidebar-hover text-sidebar-fg" : "text-sidebar-muted hover:bg-sidebar-hover/70 hover:text-sidebar-fg",
                        collapsed && "lg:justify-center lg:px-0",
                      )}
                    >
                      {active ? <span className="absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-accent" aria-hidden /> : null}
                      <Icon className="h-4 w-4 shrink-0" strokeWidth={1.75} />
                      <span className={cn("truncate", collapsed && "lg:hidden")}>{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <button
        type="button"
        onClick={onToggle}
        className="hidden h-10 items-center gap-2 border-t border-sidebar-line px-4 text-xs text-sidebar-muted hover:text-sidebar-fg lg:flex"
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? <PanelLeftOpen className="mx-auto h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        {collapsed ? null : "Collapse"}
      </button>
    </aside>
  );
}
