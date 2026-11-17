"use client";

import { Input } from "@/components/ui/field";
import { Segmented } from "@/components/ui/segmented";

export type RangeKey = "today" | "7d" | "30d" | "90d" | "custom";

export function RangePicker({ range, from, to, onChange }: { range: RangeKey; from: string; to: string; onChange: (patch: { range?: string; from?: string; to?: string }) => void }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Segmented<RangeKey>
        label="Date range"
        value={range}
        onChange={(v) => onChange({ range: v })}
        options={[
          { value: "today", label: "Today" },
          { value: "7d", label: "7D" },
          { value: "30d", label: "30D" },
          { value: "90d", label: "90D" },
          { value: "custom", label: "Custom" },
        ]}
      />
      {range === "custom" ? (
        <div className="flex items-center gap-1.5 text-xs text-muted">
          <Input compact type="date" value={from} onChange={(e) => onChange({ from: e.target.value })} aria-label="From date" className="w-[130px]" />
          <span>to</span>
          <Input compact type="date" value={to} onChange={(e) => onChange({ to: e.target.value })} aria-label="To date" className="w-[130px]" />
        </div>
      ) : null}
    </div>
  );
}

export function analyticsParams(range: RangeKey, from: string, to: string) {
  if (range === "custom") return from && to ? { range, from, to } : null;
  return { range };
}
