"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { API_BASE, api, onSessionExpired, refreshSession, setAccessToken } from "@/lib/api";
import type { Me } from "@/types";

interface SessionValue {
  me: Me | null;
  status: "loading" | "authenticated" | "anonymous";
  can: (...perms: string[]) => boolean;
  feature: (key: string) => boolean;
  reload: () => Promise<void>;
  signIn: (email: string, password: string) => Promise<{ mustChange: boolean }>;
  signOut: () => Promise<void>;
}

const Ctx = createContext<SessionValue | null>(null);

function cookie(name: string): string {
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : "";
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [bootstrapped, setBootstrapped] = useState(false);
  const [authed, setAuthed] = useState(false);
  const qc = useQueryClient();

  useEffect(() => {
    let alive = true;
    refreshSession().then((ok) => {
      if (!alive) return;
      setAuthed(ok);
      setBootstrapped(true);
    });
    const off = onSessionExpired(() => {
      setAccessToken(null);
      setAuthed(false);
      qc.clear();
    });
    return () => {
      alive = false;
      off();
    };
  }, [qc]);

  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: () => api<Me>("/auth/me"),
    enabled: bootstrapped && authed,
    staleTime: 60_000,
  });

  useEffect(() => {
    const me = meQuery.data;
    if (me?.institute) {
      const root = document.documentElement;
      root.style.setProperty("--brand", me.institute.primary_color || "#1e2a78");
      root.style.setProperty("--brand-2", me.institute.secondary_color || "#2563eb");
      root.style.setProperty("--accent", me.institute.accent_color || "#0d9488");
      const allowed = new Set(me.branches.map((b) => b.id));
      const sel = localStorage.getItem("cf.branch");
      if (sel && !allowed.has(sel)) localStorage.removeItem("cf.branch");
      if (!sel && me.branch_scoped && me.branches.length === 1) localStorage.setItem("cf.branch", me.branches[0].id);
    }
  }, [meQuery.data]);

  const can = useCallback(
    (...perms: string[]) => {
      const p = meQuery.data?.permissions ?? [];
      if (p.includes("*")) return true;
      return perms.some((x) => p.includes(x));
    },
    [meQuery.data],
  );

  const feature = useCallback((key: string) => meQuery.data?.features?.[key] ?? true, [meQuery.data]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      const res = await api<{ access_token: string; must_change_password: boolean }>("/auth/login", {
        method: "POST",
        body: { email, password },
      });
      setAccessToken(res.access_token);
      setAuthed(true);
      setBootstrapped(true);
      await qc.invalidateQueries({ queryKey: ["me"] });
      return { mustChange: res.must_change_password };
    },
    [qc],
  );

  const signOut = useCallback(async () => {
    try {
      await fetch(`${API_BASE}/auth/logout`, { method: "POST", credentials: "same-origin", headers: { "X-CSRF-Token": cookie("cf_csrf") } });
    } finally {
      setAccessToken(null);
      setAuthed(false);
      localStorage.removeItem("cf.branch");
      qc.clear();
    }
  }, [qc]);

  const value = useMemo<SessionValue>(
    () => ({
      me: meQuery.data ?? null,
      status: !bootstrapped || (authed && meQuery.isLoading) ? "loading" : authed && meQuery.data ? "authenticated" : "anonymous",
      can,
      feature,
      reload: async () => {
        await meQuery.refetch();
      },
      signIn,
      signOut,
    }),
    [meQuery, bootstrapped, authed, can, feature, signIn, signOut],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSession(): SessionValue {
  const v = useContext(Ctx);
  if (!v) throw new Error("useSession must be used within SessionProvider");
  return v;
}
