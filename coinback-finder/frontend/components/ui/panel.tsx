import type { ReactNode } from "react";

import { cn } from "@/services/cn";

export function Panel({ children, className }: { children: ReactNode; className?: string }) {
  return <section className={cn("rounded-md border border-line bg-surface", className)}>{children}</section>;
}

export function PanelHeader({ title, description, actions, className }: { title: ReactNode; description?: ReactNode; actions?: ReactNode; className?: string }) {
  return (
    <header className={cn("flex min-h-[40px] items-center justify-between gap-3 border-b border-line px-3 py-2", className)}>
      <div className="min-w-0">
        <h2 className="truncate text-sm font-semibold text-fg">{title}</h2>
        {description ? <p className="truncate text-2xs text-faint">{description}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-1.5">{actions}</div> : null}
    </header>
  );
}

export function PanelBody({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("p-3", className)}>{children}</div>;
}

export function KeyValue({ items, className }: { items: { label: ReactNode; value: ReactNode; hint?: ReactNode }[]; className?: string }) {
  return (
    <dl className={cn("divide-y divide-line", className)}>
      {items.map((item, i) => (
        <div key={i} className="flex items-start justify-between gap-4 py-1.5">
          <dt className="shrink-0 text-xs text-muted">
            {item.label}
            {item.hint ? <span className="block text-2xs text-faint">{item.hint}</span> : null}
          </dt>
          <dd className="num min-w-0 text-right text-sm text-fg">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}
