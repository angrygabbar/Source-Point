"use client";

import { cn } from "@/services/cn";

export function Segmented<T extends string>({
  value,
  onChange,
  options,
  size = "sm",
  label,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string; title?: string }[];
  size?: "xs" | "sm";
  label?: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex items-center rounded border border-line-strong/70 bg-surface p-0.5">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          role="radio"
          aria-checked={value === opt.value}
          title={opt.title}
          onClick={() => onChange(opt.value)}
          className={cn(
            "rounded-sm font-medium transition-colors",
            size === "xs" ? "h-5 px-1.5 text-2xs" : "h-6 px-2 text-xs",
            value === opt.value ? "bg-subtle text-fg shadow-[inset_0_0_0_1px_hsl(var(--line-strong))]" : "text-muted hover:text-fg",
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
