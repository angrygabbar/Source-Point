"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { Search, X } from "lucide-react";

import { Input, Select } from "@/components/ui/field";
import { cn } from "@/services/cn";

export function SearchInput({ value, onChange, placeholder = "Search", className }: { value: string; onChange: (v: string) => void; placeholder?: string; className?: string }) {
  const [text, setText] = useState(value);
  const timer = useRef<number>();
  useEffect(() => setText(value), [value]);
  useEffect(() => () => window.clearTimeout(timer.current), []);
  return (
    <div className={cn("relative w-full max-w-[280px]", className)}>
      <Search className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint" aria-hidden />
      <Input
        compact
        value={text}
        maxLength={200}
        placeholder={placeholder}
        aria-label={placeholder}
        className="pl-7 pr-6"
        onChange={(e) => {
          const next = e.target.value;
          setText(next);
          window.clearTimeout(timer.current);
          timer.current = window.setTimeout(() => onChange(next.trim()), 300);
        }}
      />
      {text ? (
        <button
          type="button"
          aria-label="Clear search"
          className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded p-0.5 text-faint hover:text-fg"
          onClick={() => {
            setText("");
            onChange("");
          }}
        >
          <X className="h-3 w-3" />
        </button>
      ) : null}
    </div>
  );
}

export function FilterSelect({
  label,
  value,
  onChange,
  options,
  allLabel = "All",
  className,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  allLabel?: string;
  className?: string;
}) {
  return (
    <label className={cn("flex items-center gap-1.5 text-xs text-muted", className)}>
      <span className="whitespace-nowrap">{label}</span>
      <Select compact value={value} onChange={(e) => onChange(e.target.value)} className="min-w-[110px]" aria-label={label}>
        <option value="">{allLabel}</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </Select>
    </label>
  );
}

export function NumberFilter({ label, value, onChange, placeholder, width = 76, step }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string; width?: number; step?: string }) {
  const [text, setText] = useState(value);
  useEffect(() => setText(value), [value]);
  return (
    <label className="flex items-center gap-1.5 text-xs text-muted">
      <span className="whitespace-nowrap">{label}</span>
      <Input
        compact
        type="number"
        min={0}
        step={step}
        value={text}
        placeholder={placeholder}
        style={{ width }}
        aria-label={label}
        onChange={(e) => setText(e.target.value)}
        onBlur={() => text !== value && onChange(text)}
        onKeyDown={(e) => e.key === "Enter" && onChange(text)}
      />
    </label>
  );
}

export function FilterGroup({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("flex flex-wrap items-center gap-x-3 gap-y-2", className)}>{children}</div>;
}
