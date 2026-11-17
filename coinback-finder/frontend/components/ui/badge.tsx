import type { ReactNode } from "react";

import { cn } from "@/services/cn";

export type Tone = "neutral" | "accent" | "positive" | "warning" | "negative" | "muted";

const tones: Record<Tone, string> = {
  neutral: "bg-subtle text-fg border-line",
  accent: "bg-accent-soft text-accent border-accent/25",
  positive: "bg-positive-soft text-positive border-positive/25",
  warning: "bg-warning-soft text-warning border-warning/25",
  negative: "bg-negative-soft text-negative border-negative/25",
  muted: "bg-transparent text-faint border-line",
};
const dots: Record<Tone, string> = {
  neutral: "bg-muted",
  accent: "bg-accent",
  positive: "bg-positive",
  warning: "bg-warning",
  negative: "bg-negative",
  muted: "bg-faint",
};

export function Badge({ tone = "neutral", dot, children, className, title }: { tone?: Tone; dot?: boolean; children: ReactNode; className?: string; title?: string }) {
  return (
    <span title={title} className={cn("inline-flex h-5 items-center gap-1.5 whitespace-nowrap rounded-sm border px-1.5 text-2xs font-medium", tones[tone], className)}>
      {dot ? <span className={cn("h-1.5 w-1.5 rounded-full", dots[tone])} aria-hidden /> : null}
      {children}
    </span>
  );
}

export function StatusDot({ tone, pulse }: { tone: Tone; pulse?: boolean }) {
  return (
    <span className="relative inline-flex h-2 w-2">
      {pulse ? <span className={cn("absolute inline-flex h-full w-full animate-ping rounded-full opacity-50", dots[tone])} /> : null}
      <span className={cn("relative inline-flex h-2 w-2 rounded-full", dots[tone])} />
    </span>
  );
}
