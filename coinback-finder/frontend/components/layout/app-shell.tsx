"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";

import { THEME_KEY, useTheme } from "@/app/providers";
import { useApi } from "@/hooks/use-api";
import { useLocalStorage } from "@/hooks/use-local-storage";
import { cn } from "@/services/cn";
import type { AppSettings, Envelope } from "@/services/types";
import { CommandPalette } from "./command-palette";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

export function AppShell({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useLocalStorage("cbf:sidebar-collapsed", false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const pathname = usePathname();
  const { setTheme } = useTheme();
  const settings = useApi<Envelope<AppSettings>>("/settings");

  useEffect(() => {
    const preferred = settings.data?.data.default_theme;
    if (preferred && !window.localStorage.getItem(THEME_KEY)) setTheme(preferred);
  }, [settings.data, setTheme]);

  useEffect(() => setMobileOpen(false), [pathname]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="min-h-screen">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} mobileOpen={mobileOpen} onNavigate={() => setMobileOpen(false)} />
      {mobileOpen ? <div className="fixed inset-0 z-30 bg-black/40 lg:hidden" onClick={() => setMobileOpen(false)} aria-hidden /> : null}
      <div className={cn("flex min-h-screen flex-col transition-[padding] duration-150", collapsed ? "lg:pl-14" : "lg:pl-56")}>
        <Topbar onMenu={() => setMobileOpen(true)} onSearch={() => setPaletteOpen(true)} />
        <main className="flex-1 px-3 py-4 lg:px-5">{children}</main>
      </div>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
}
