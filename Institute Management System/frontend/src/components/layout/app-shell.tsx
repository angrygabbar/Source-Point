"use client";

import { useQuery } from "@tanstack/react-query";
import { Bell, Building2, ChevronDown, GraduationCap, LogOut, Menu as MenuIcon, Search, User, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Button, Menu, Select } from "@/components/ui";
import { useSession } from "@/hooks/use-session";
import { api, withBasePath } from "@/lib/api";
import { NAV, type NavItem } from "@/lib/nav";
import { cn } from "@/lib/utils";

function useVisibleNav() {
  const { me, can, feature } = useSession();
  return useMemo(() => {
    if (!me) return [];
    const portal = me.portal === "platform" ? "admin" : me.portal;
    const visible = (i: NavItem) => {
      if (i.portals && !i.portals.includes(portal)) return false;
      if (i.feature && !feature(i.feature)) return false;
      if (i.module && !can(`${i.module}.read`, `${i.module}.read_own`)) return false;
      if (i.perms && !can(...i.perms)) return false;
      return true;
    };
    return NAV.map((g) => ({ ...g, items: g.items.filter(visible) })).filter((g) => g.items.length);
  }, [me, can, feature]);
}

function BranchSelector() {
  const { me } = useSession();
  const [value, setValue] = useState<string>("");
  useEffect(() => setValue(localStorage.getItem("cf.branch") ?? ""), []);
  if (!me || me.branches.length <= 1) return null;
  return (
    <div className="hidden items-center gap-1.5 md:flex">
      <Building2 className="h-4 w-4 text-slate-400" />
      <Select
        aria-label="Branch"
        className="h-8 w-44 text-xs"
        value={value}
        onChange={(e) => {
          if (e.target.value) localStorage.setItem("cf.branch", e.target.value);
          else localStorage.removeItem("cf.branch");
          window.location.reload();
        }}
      >
        {!me.branch_scoped && <option value="">All branches</option>}
        {me.branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
      </Select>
    </div>
  );
}

function AcademicYearSelector() {
  const { can } = useSession();
  const years = useQuery({
    queryKey: ["academic-years-shell"],
    queryFn: () => api<{ items: { id: string; name: string; is_current: boolean }[] }>("/academic-years", { query: { page_size: 20, sort: "-start_date" } }),
    enabled: can("academic_years.read"),
    staleTime: 10 * 60_000,
  });
  const [value, setValue] = useState("");
  useEffect(() => setValue(localStorage.getItem("cf.year") ?? ""), []);
  useEffect(() => {
    if (!value && years.data?.items.length) {
      const cur = years.data.items.find((y) => y.is_current) ?? years.data.items[0];
      localStorage.setItem("cf.year", cur.id);
      setValue(cur.id);
    }
  }, [years.data, value]);
  if (!years.data?.items.length) return null;
  return (
    <Select
      aria-label="Academic year"
      className="hidden h-8 w-32 text-xs md:block"
      value={value}
      onChange={(e) => {
        localStorage.setItem("cf.year", e.target.value);
        setValue(e.target.value);
      }}
    >
      {years.data.items.map((y) => <option key={y.id} value={y.id}>{y.name}{y.is_current ? " (current)" : ""}</option>)}
    </Select>
  );
}

function NotificationBell() {
  const router = useRouter();
  const count = useQuery({
    queryKey: ["unread-count"],
    queryFn: () => api<{ count: number }>("/notifications/unread-count"),
    refetchInterval: 60_000,
  });
  return (
    <button aria-label="Notifications" className="relative rounded-lg p-2 text-slate-500 hover:bg-slate-100" onClick={() => router.push("/notifications")}>
      <Bell className="h-5 w-5" />
      {!!count.data?.count && (
        <span className="absolute -right-0.5 -top-0.5 rounded-full bg-red-600 px-1.5 text-[10px] font-semibold text-white">
          {count.data.count > 99 ? "99+" : count.data.count}
        </span>
      )}
    </button>
  );
}

function Breadcrumbs() {
  const path = usePathname();
  const parts = path.split("/").filter(Boolean).filter((p) => p !== "r");
  return (
    <nav className="hidden text-xs text-slate-500 lg:block" aria-label="Breadcrumb">
      <Link href="/dashboard" className="hover:text-slate-800">Home</Link>
      {parts.map((p, i) => (
        <span key={i}>
          <span className="mx-1.5">/</span>
          <span className={i === parts.length - 1 ? "text-slate-700" : ""}>{/^[0-9a-f-]{36}$/.test(p) ? "Details" : p.replace(/-/g, " ")}</span>
        </span>
      ))}
    </nav>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const { me, signOut } = useSession();
  const groups = useVisibleNav();
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const logo = useQuery({
    queryKey: ["logo", me?.institute?.id],
    queryFn: async () => {
      const { apiResponse } = await import("@/lib/api");
      const res = await apiResponse("/institutes/current/logo");
      return URL.createObjectURL(await res.blob());
    },
    enabled: !!me?.institute?.has_logo,
    staleTime: Infinity,
  });

  useEffect(() => setOpen(false), [pathname]);

  const sidebar = (
    <aside className="flex h-full w-64 flex-col text-slate-200" style={{ background: "var(--brand)" }}>
      <div className="flex items-center gap-2.5 px-4 py-4">
        {logo.data ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={logo.data} alt="" className="h-9 w-9 rounded-lg bg-white object-contain p-0.5" />
        ) : (
          <div className="rounded-lg bg-white/10 p-2"><GraduationCap className="h-5 w-5 text-white" /></div>
        )}
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-white">{me?.institute?.name ?? "Institute Management System"}</p>
          <p className="text-[11px] text-indigo-200">Institute Management System</p>
        </div>
      </div>
      <nav className="flex-1 space-y-4 overflow-y-auto px-2 pb-6">
        {groups.map((g) => (
          <div key={g.label}>
            <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-indigo-300/80">{g.label}</p>
            {g.items.map((i) => {
              const active = pathname === i.href || (i.href !== "/dashboard" && pathname.startsWith(i.href + "/"));
              return (
                <Link
                  key={i.href}
                  href={i.href}
                  className={cn(
                    "flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-[13px] transition-colors",
                    active ? "bg-white/15 font-medium text-white" : "text-indigo-100/90 hover:bg-white/10 hover:text-white",
                  )}
                >
                  <i.icon className="h-4 w-4 shrink-0" />
                  {i.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );

  return (
    <div className="flex h-screen overflow-hidden">
      <div className="hidden lg:block">{sidebar}</div>
      {open && (
        <div className="fixed inset-0 z-40 flex lg:hidden">
          <div className="absolute inset-0 bg-slate-900/50" onClick={() => setOpen(false)} />
          <div className="relative z-50">{sidebar}</div>
          <button className="relative z-50 m-2 h-9 rounded-lg bg-white p-2" onClick={() => setOpen(false)} aria-label="Close menu"><X className="h-5 w-5" /></button>
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-slate-200 bg-white px-3 lg:px-6">
          <button className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu">
            <MenuIcon className="h-5 w-5" />
          </button>
          <Breadcrumbs />
          <div className="flex-1" />
          {(me?.portal === "admin" || me?.portal === "teacher") && (
            <form
              className="relative hidden sm:block"
              onSubmit={(e) => {
                e.preventDefault();
                if (q.trim().length >= 2) router.push(`/search?q=${encodeURIComponent(q.trim())}`);
              }}
            >
              <Search className="pointer-events-none absolute left-2.5 top-2 h-4 w-4 text-slate-400" />
              <input className="input h-8 w-56 pl-8 text-xs" placeholder="Search students, invoices, classes…" value={q} onChange={(e) => setQ(e.target.value)} />
            </form>
          )}
          <AcademicYearSelector />
          <BranchSelector />
          <NotificationBell />
          <Menu
            trigger={
              <button className="flex items-center gap-2 rounded-lg px-2 py-1 hover:bg-slate-100">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-xs font-semibold text-brand-800">
                  {me?.user.full_name.split(" ").map((x) => x[0]).slice(0, 2).join("").toUpperCase()}
                </span>
                <span className="hidden text-left md:block">
                  <span className="block text-xs font-medium text-slate-800">{me?.user.full_name}</span>
                  <span className="block text-[11px] capitalize text-slate-500">{me?.portal}</span>
                </span>
                <ChevronDown className="h-4 w-4 text-slate-400" />
              </button>
            }
            items={[
              { label: "My profile & security", icon: <User className="h-4 w-4" />, onClick: () => router.push("/profile") },
              { label: "Platform administration", hidden: !me?.user.is_superuser, onClick: () => { localStorage.removeItem("cf.institute"); localStorage.removeItem("cf.branch"); window.location.href = withBasePath("/platform"); } },
              { label: "Sign out", icon: <LogOut className="h-4 w-4" />, danger: true, onClick: async () => { await signOut(); router.replace("/login"); } },
            ]}
          />
        </header>
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-[1400px] p-4 lg:p-6">{children}</div>
        </main>
        <MobileNav />
      </div>
    </div>
  );
}

function MobileNav() {
  const { me } = useSession();
  const pathname = usePathname();
  if (!me) return null;
  const items =
    me.portal === "teacher"
      ? [["/dashboard", "Home"], ["/timetable", "Classes"], ["/r/assignments", "Homework"], ["/messages", "Messages"]]
      : me.portal === "admin"
        ? [["/dashboard", "Home"], ["/timetable", "Timetable"], ["/r/students", "Students"], ["/finance/collect", "Collect"]]
        : [["/dashboard", "Home"], ["/timetable", "Timetable"], ["/r/assignments", "Homework"], ["/r/invoices", "Fees"]];
  return (
    <nav className="grid grid-cols-4 border-t border-slate-200 bg-white lg:hidden">
      {items.map(([href, label]) => (
        <Link key={href} href={href} className={cn("py-2.5 text-center text-xs font-medium", pathname.startsWith(href) ? "text-brand-800" : "text-slate-500")}>
          {label}
        </Link>
      ))}
    </nav>
  );
}

export function PortalGuard({ children }: { children: ReactNode }) {
  const { status, me } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  useEffect(() => {
    if (status === "anonymous") router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    if (status === "authenticated" && me?.user.must_change_password && pathname !== "/profile") router.replace("/profile?force=1");
    if (status === "authenticated" && me?.portal === "platform" && !pathname.startsWith("/platform") && pathname !== "/profile") router.replace("/platform");
  }, [status, me, router, pathname]);
  if (status !== "authenticated") {
    return (
      <div className="flex h-screen items-center justify-center text-sm text-slate-500">
        <Button variant="ghost" loading>Loading Institute Management…</Button>
      </div>
    );
  }
  return <>{children}</>;
}
