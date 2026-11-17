"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ToastProvider } from "@/components/ui/toast";
import type { ApiError } from "@/services/api";

type Theme = "light" | "dark";
const ThemeContext = createContext<{ theme: Theme; setTheme: (t: Theme) => void; toggle: () => void } | null>(null);
export const THEME_KEY = "cbf:theme";

function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("light");
  useEffect(() => {
    setThemeState(document.documentElement.classList.contains("dark") ? "dark" : "light");
  }, []);
  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    document.documentElement.classList.toggle("dark", t === "dark");
    try {
      localStorage.setItem(THEME_KEY, t);
    } catch {
      /* ignore */
    }
  }, []);
  const toggle = useCallback(() => setTheme(theme === "dark" ? "light" : "dark"), [theme, setTheme]);
  return <ThemeContext.Provider value={{ theme, setTheme, toggle }}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within Providers");
  return ctx;
}

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 20_000,
            refetchOnWindowFocus: true,
            retry: (count, error) => {
              const status = (error as ApiError).status;
              return status !== 401 && status !== 403 && status !== 404 && status !== 422 && count < 2;
            },
          },
        },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <ThemeProvider>
        <ToastProvider>{children}</ToastProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
