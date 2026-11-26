"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bell, LogOut, Menu, Moon, Search, Settings, Sun, User } from "lucide-react";

import { useTheme } from "@/app/providers";
import { StatusDot } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MenuItem, MenuLabel, MenuSeparator, Popover } from "@/components/ui/popover";
import { useApi } from "@/hooks/use-api";
import { formatDateTimeShort, formatRelative, formatTime } from "@/services/format";
import type { CurrentUser, Envelope, NotificationItem, Paged, ScannerStatus } from "@/services/types";

function ScannerIndicator() {
  const { data } = useApi<Envelope<ScannerStatus>>("/dashboard/scanner-status", undefined, { refetchInterval: 20_000 });
  const s = data?.data;
  const tone = !s ? "muted" : s.state === "running" ? "accent" : s.state === "idle" ? "positive" : "negative";
  const label = !s ? "Scanner" : s.state === "running" ? "Scanning" : s.state === "idle" ? "Scanner idle" : "Scanner offline";
  const last = s?.last_run?.finished_at;
  return (
    <Link
      href="/scanner"
      className="hidden items-center gap-2.5 rounded border border-line px-2.5 py-1 text-xs hover:bg-subtle md:flex"
      title={s?.alive_at ? `Heartbeat ${formatDateTimeShort(s.alive_at)}` : "No scanner heartbeat recorded"}
    >
      <StatusDot tone={tone} pulse={s?.state === "running"} />
      <span className="font-medium text-fg">{label}</span>
      {s?.state === "running" && s.current_run?.progress?.total ? (
        <span className="num text-muted">
          {s.current_run.progress.phase} {s.current_run.progress.done}/{s.current_run.progress.total}
        </span>
      ) : null}
      <span className="h-3 w-px bg-line" />
      <span className="text-muted">
        Last <span className="num text-fg">{last ? formatRelative(last) : "never"}</span>
      </span>
      <span className="text-muted">
        Next <span className="num text-fg">{s?.next_scan_at && s.alive ? formatTime(s.next_scan_at) : "not scheduled"}</span>
      </span>
    </Link>
  );
}

function NotificationBell() {
  const { data } = useApi<Paged<NotificationItem>>("/notifications", { status: "FAILED,PENDING", page_size: 1 }, { refetchInterval: 60_000 });
  const count = data?.meta.total ?? 0;
  return (
    <Link href="/notifications" className="relative inline-flex h-8 w-8 items-center justify-center rounded text-muted hover:bg-subtle hover:text-fg" aria-label={`Notifications${count ? `, ${count} pending or failed` : ""}`}>
      <Bell className="h-4 w-4" />
      {count ? <span className="num absolute -right-0.5 -top-0.5 min-w-[16px] rounded-full bg-negative px-1 text-center text-[10px] font-semibold leading-4 text-white">{count > 99 ? "99+" : count}</span> : null}
    </Link>
  );
}

export function Topbar({ onMenu, onSearch }: { onMenu: () => void; onSearch: () => void }) {
  const router = useRouter();
  const { theme, toggle } = useTheme();
  const me = useApi<Envelope<CurrentUser>>("/auth/me");

  const signOut = async () => {
    window.location.assign("/logout");
  };

  return (
    <header className="sticky top-0 z-30 flex h-14 min-w-0 items-center gap-1.5 border-b border-line bg-surface/95 px-2.5 backdrop-blur supports-[backdrop-filter]:bg-surface/80 sm:gap-2 sm:px-3 lg:h-12 lg:px-4">
      <Button size="icon" variant="ghost" className="lg:hidden" onClick={onMenu} aria-label="Open navigation">
        <Menu className="h-4 w-4" />
      </Button>
      <button
        type="button"
        onClick={onSearch}
        className="flex h-9 min-w-0 flex-1 items-center gap-1.5 rounded border border-line-strong/70 bg-canvas px-2 text-left text-xs text-faint hover:border-line-strong sm:h-8 sm:max-w-sm sm:gap-2 sm:px-2.5 sm:text-sm"
      >
        <Search className="h-3.5 w-3.5" />
        <span className="flex-1 truncate">Search products, brands, pages</span>
        <kbd className="hidden rounded border border-line bg-surface px-1.5 text-2xs text-muted sm:inline">Ctrl K</kbd>
      </button>
      <div className="ml-auto flex shrink-0 items-center gap-0.5 sm:gap-1.5">
        <ScannerIndicator />
        <NotificationBell />
        <Button size="icon" variant="ghost" onClick={toggle} aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}>
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
        <Popover
          align="right"
          trigger={({ toggle: open }) => (
            <Button size="sm" variant="ghost" onClick={open} aria-label="Account menu">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-subtle text-muted">
                <User className="h-3.5 w-3.5" />
              </span>
              <span className="hidden text-sm text-fg sm:inline">{me.data?.data.username ?? "Account"}</span>
            </Button>
          )}
        >
          {(close) => (
            <>
              <MenuLabel>Signed in as {me.data?.data.username ?? "…"}</MenuLabel>
              <MenuItem
                icon={<Settings className="h-3.5 w-3.5" />}
                onClick={() => {
                  close();
                  router.push("/settings");
                }}
              >
                Settings
              </MenuItem>
              <MenuSeparator />
              <MenuItem icon={<LogOut className="h-3.5 w-3.5" />} onClick={signOut}>
                Sign out
              </MenuItem>
            </>
          )}
        </Popover>
      </div>
    </header>
  );
}
