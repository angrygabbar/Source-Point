"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { CheckCircle2, Info, X, XCircle } from "lucide-react";

import { cn } from "@/services/cn";

type ToastTone = "positive" | "negative" | "neutral";
interface ToastItem {
  id: number;
  title: string;
  description?: string;
  tone: ToastTone;
}

const ToastContext = createContext<{ push: (t: Omit<ToastItem, "id" | "tone"> & { tone?: ToastTone }) => void } | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const dismiss = useCallback((id: number) => setItems((list) => list.filter((t) => t.id !== id)), []);
  const push = useCallback(
    (t: Omit<ToastItem, "id" | "tone"> & { tone?: ToastTone }) => {
      const id = Date.now() + Math.random();
      setItems((list) => [...list.slice(-3), { id, tone: t.tone ?? "neutral", title: t.title, description: t.description }]);
      window.setTimeout(() => dismiss(id), t.tone === "negative" ? 7000 : 4000);
    },
    [dismiss],
  );
  const value = useMemo(() => ({ push }), [push]);
  const icons = { positive: CheckCircle2, negative: XCircle, neutral: Info };
  const colors = { positive: "text-positive", negative: "text-negative", neutral: "text-accent" };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-[340px] flex-col gap-2" aria-live="polite">
        {items.map((t) => {
          const Icon = icons[t.tone];
          return (
            <div key={t.id} className="pointer-events-auto flex items-start gap-2 rounded-md border border-line bg-surface px-3 py-2.5 shadow-pop">
              <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", colors[t.tone])} />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium">{t.title}</p>
                {t.description ? <p className="mt-0.5 break-words text-xs text-muted">{t.description}</p> : null}
              </div>
              <button type="button" className="text-faint hover:text-fg" onClick={() => dismiss(t.id)} aria-label="Dismiss">
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
