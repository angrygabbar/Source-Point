"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

import { cn } from "@/services/cn";

export function Popover({
  trigger,
  children,
  align = "left",
  className,
}: {
  trigger: (props: { open: boolean; toggle: () => void }) => ReactNode;
  children: ReactNode | ((close: () => void) => ReactNode);
  align?: "left" | "right";
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (root.current && !root.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const close = () => setOpen(false);
  return (
    <div ref={root} className="relative inline-block">
      {trigger({ open, toggle: () => setOpen((v) => !v) })}
      {open ? (
        <div
          className={cn(
            "absolute z-40 mt-1 min-w-[180px] rounded-md border border-line bg-surface p-1 shadow-pop",
            align === "right" ? "right-0" : "left-0",
            className,
          )}
        >
          {typeof children === "function" ? children(close) : children}
        </div>
      ) : null}
    </div>
  );
}

export function MenuItem({ children, onClick, icon, tone, disabled }: { children: ReactNode; onClick?: () => void; icon?: ReactNode; tone?: "negative"; disabled?: boolean }) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-subtle disabled:opacity-50",
        tone === "negative" ? "text-negative" : "text-fg",
      )}
    >
      {icon ? <span className="text-faint">{icon}</span> : null}
      {children}
    </button>
  );
}

export function MenuLabel({ children }: { children: ReactNode }) {
  return <div className="eyebrow px-2 pb-1 pt-1.5">{children}</div>;
}

export function MenuSeparator() {
  return <div className="my-1 h-px bg-line" />;
}
