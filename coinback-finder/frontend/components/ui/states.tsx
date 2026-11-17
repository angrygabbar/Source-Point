import type { ReactNode } from "react";
import { AlertTriangle, Inbox } from "lucide-react";

import { cn } from "@/services/cn";
import { Button } from "./button";

export function NA({ label = "Not available", className }: { label?: string; className?: string }) {
  return <span className={cn("text-xs text-faint", className)}>{label}</span>;
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-sm bg-subtle", className)} />;
}

export function EmptyState({ title, description, action, icon, className }: { title: string; description?: ReactNode; action?: ReactNode; icon?: ReactNode; className?: string }) {
  return (
    <div className={cn("flex flex-col items-center justify-center px-6 py-10 text-center", className)}>
      <div className="mb-2 text-faint">{icon ?? <Inbox className="h-5 w-5" />}</div>
      <p className="text-sm font-medium text-fg">{title}</p>
      {description ? <div className="mt-1 max-w-md text-xs text-muted">{description}</div> : null}
      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  );
}

export function ErrorState({ message, onRetry, className }: { message?: string; onRetry?: () => void; className?: string }) {
  return (
    <div className={cn("flex flex-col items-center justify-center px-6 py-10 text-center", className)}>
      <AlertTriangle className="mb-2 h-5 w-5 text-negative" />
      <p className="text-sm font-medium">Could not load data</p>
      <p className="mt-1 max-w-md text-xs text-muted">{message || "The request failed."}</p>
      {onRetry ? (
        <Button size="sm" className="mt-3" onClick={onRetry}>
          Retry
        </Button>
      ) : null}
    </div>
  );
}

export function Notice({ tone = "neutral", title, children, className }: { tone?: "neutral" | "warning" | "negative" | "accent"; title?: string; children: ReactNode; className?: string }) {
  const tones = {
    neutral: "border-line bg-subtle text-fg",
    warning: "border-warning/30 bg-warning-soft text-fg",
    negative: "border-negative/30 bg-negative-soft text-fg",
    accent: "border-accent/25 bg-accent-soft text-fg",
  };
  return (
    <div className={cn("rounded-md border px-3 py-2 text-xs leading-5", tones[tone], className)}>
      {title ? <p className="font-semibold">{title}</p> : null}
      <div className="text-muted">{children}</div>
    </div>
  );
}
